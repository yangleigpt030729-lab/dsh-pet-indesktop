"""Exercise the actual probe script with only the unavailable Win32 API replaced."""
import contextlib
import io
import json
import sys
from types import SimpleNamespace

import pytest

from tests.test_ffmpeg_windows_console import _CONSOLE_PROBE, _assert_no_console


def run_probe(monkeypatch, *, own_console, target_console, free_succeeds=True):
    state = {'own': own_console, 'error': 0}
    calls = []

    def free():
        calls.append('FreeConsole')
        if not free_succeeds:
            state['error'] = 5
            return 0
        state['own'] = False
        return 1

    def window():
        calls.append('GetConsoleWindow')
        return 123 if state['own'] else 0

    def attach(_pid):
        calls.append('AttachConsole')
        if state['own']:
            state['error'] = 5
            return 0
        if target_console:
            state['own'] = True
            return 1
        state['error'] = 6
        return 0

    kernel = SimpleNamespace(FreeConsole=free, GetConsoleWindow=window, AttachConsole=attach)
    fake = SimpleNamespace(WinDLL=lambda *_a, **_kw: kernel, c_uint32=int,
                           c_int=int, c_void_p=int, get_last_error=lambda: state['error'],
                           set_last_error=lambda value: state.update(error=value),
                           WinError=lambda error: OSError(error, 'synthetic Win32 error'))
    monkeypatch.setitem(sys.modules, 'ctypes', fake)
    monkeypatch.setattr(sys, 'argv', ['probe', '12345'])
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(compile(_CONSOLE_PROBE, '<console-probe>', 'exec'), {})
    return json.loads(output.getvalue()), calls


@pytest.mark.parametrize('own_console', [True, False])
def test_probe_detaches_itself_before_testing_consoleless_target(monkeypatch, own_console):
    result, calls = run_probe(monkeypatch, own_console=own_console, target_console=False)
    assert result['error'] == 6, result  # own console used to incorrectly produce ERROR_ACCESS_DENIED
    assert not result['attached']
    assert calls[0] == 'FreeConsole'
    _assert_no_console(result, SimpleNamespace(pid=12345, poll=lambda: None))


def test_probe_still_detects_target_with_a_console(monkeypatch):
    result, calls = run_probe(monkeypatch, own_console=True, target_console=True)
    assert result['attached'] is True
    assert calls[0] == 'FreeConsole'
    with pytest.raises(AssertionError, match='FFmpeg has a console'):
        _assert_no_console(result, SimpleNamespace(pid=12345, poll=lambda: None))


def test_failed_free_console_aborts_probe(monkeypatch):
    with pytest.raises(OSError):
        run_probe(monkeypatch, own_console=True, target_console=False, free_succeeds=False)


@pytest.mark.parametrize(('result', 'returncode'), [
    ({'detached': True, 'attached': False, 'error': 5}, None),
    ({'detached': False, 'attached': False, 'error': 6}, None),
    ({'detached': True, 'attached': False, 'error': 87}, None),
])
def test_uncertain_results_remain_failures(result, returncode):
    with pytest.raises(AssertionError):
        _assert_no_console(result, SimpleNamespace(pid=12345, poll=lambda: returncode))


def test_exited_target_keeps_original_race_handling():
    _assert_no_console({'detached': True, 'attached': False, 'error': 87},
                       SimpleNamespace(pid=12345, poll=lambda: 0))
