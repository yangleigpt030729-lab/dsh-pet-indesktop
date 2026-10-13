"""Windows process policy at real SDK entry points; only the OS spawn is recorded."""
import subprocess
import sys
import inspect
import threading
from pathlib import Path
from types import SimpleNamespace

import imageio_ffmpeg
import pytest

from pet import animation_thumbnail, frameseq_provision as provision, webm_clip

NO_WINDOW = 0x08000000
LOW_PRIORITY = 0x00004000


@pytest.fixture
def windows_spawn(monkeypatch):
    webm_clip._PopenCapture._install()
    calls = []
    adopted = []

    class Process:
        def __init__(self, args, **kwargs):
            calls.append((args, kwargs))
            self.args = args
            self.pid = 0
            self.returncode = 0

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def communicate(self, *_args, **_kwargs):
            return b'version output', b''

        def poll(self):
            return self.returncode

        def wait(self, **_kwargs):
            return self.returncode

        def kill(self):
            self.returncode = -1

    monkeypatch.setattr(webm_clip, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(provision, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(subprocess, 'CREATE_NO_WINDOW', NO_WINDOW, raising=False)
    monkeypatch.setattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', LOW_PRIORITY, raising=False)
    monkeypatch.setattr(webm_clip._PopenCapture, '_real_popen', Process)
    monkeypatch.setattr(webm_clip.win_job, 'adopt', adopted.append)
    return calls, adopted


def test_conversion_keeps_low_priority_and_hides_console(windows_spawn):
    assert provision._creation_flags() == NO_WINDOW | LOW_PRIORITY


@pytest.mark.parametrize('entry', ['Popen', 'call', 'check_call', 'check_output', 'run'])
@pytest.mark.parametrize('module', ['_io', '_utils'])
def test_sdk_all_spawn_forms_are_scoped_hidden_and_adopted(windows_spawn, module, entry):
    sdk = getattr(imageio_ffmpeg, module).subprocess
    startup = object()
    with webm_clip._PopenCapture() as capture:
        result = getattr(sdk, entry)([r'D:\app\ffmpeg-win-x86_64-v7.1.exe', '-version'],
                                   creationflags=0x200, startupinfo=startup)
    calls, adopted = windows_spawn
    assert len(calls) == len(adopted) == 1
    assert calls[0][1]['creationflags'] == NO_WINDOW | 0x200
    assert calls[0][1]['startupinfo'] is startup
    assert capture.process is adopted[0]
    if entry == 'check_output':
        assert result == b'version output'


def test_executable_validation_real_sdk_calls_hidden_process(windows_spawn):
    assert imageio_ffmpeg._utils._is_valid_exe('ffmpeg.exe')
    calls, adopted = windows_spawn
    assert calls[0][0] == ['ffmpeg.exe', '-version']
    assert calls[0][1]['creationflags'] & NO_WINDOW
    assert len(adopted) == 1


def test_conversion_spawn_uses_same_job_and_console_policy(windows_spawn):
    proc = provision._popen(['ffmpeg.exe', '-i', 'synthetic.webm'],
                            creationflags=LOW_PRIORITY, stdout=subprocess.PIPE)
    calls, adopted = windows_spawn
    assert adopted == [proc]
    assert calls[0][1]['creationflags'] == NO_WINDOW | LOW_PRIORITY
    assert calls[0][1]['stdout'] == subprocess.PIPE


def test_proxy_does_not_change_global_subprocess_class_or_helpers(windows_spawn):
    assert isinstance(subprocess.Popen, type)
    assert subprocess.run.__globals__ is subprocess.__dict__
    assert subprocess.check_output.__globals__ is subprocess.__dict__
    assert imageio_ffmpeg._io.subprocess is not subprocess
    assert imageio_ffmpeg._utils.subprocess is not subprocess
    assert issubclass(type('Child', (subprocess.Popen,), {}), subprocess.Popen)
    original = imageio_ffmpeg._io.subprocess
    webm_clip._PopenCapture._install()
    assert imageio_ffmpeg._io.subprocess is original


@pytest.mark.parametrize('entry', ['probe_fps', 'ffmpeg_exe', 'thumbnail', 'warm_exe', 'metadata'])
def test_cold_entry_installs_policy_before_calling_sdk(monkeypatch, tmp_path, entry):
    installed = []
    monkeypatch.setattr(webm_clip._PopenCapture, '_install', lambda: installed.append(True))

    def check(*_args, **_kwargs):
        assert installed, 'cold SDK spawn bypassed the product process policy'
        if entry == 'metadata':
            return 1, 1.0
        if entry in ('ffmpeg_exe', 'warm_exe'):
            return 'ffmpeg.exe'
        return iter([{'fps': 1, 'duration': 1, 'size': (1, 1)}, bytes(4)])

    monkeypatch.setattr(imageio_ffmpeg, 'read_frames', check)
    monkeypatch.setattr(imageio_ffmpeg, 'get_ffmpeg_exe', check)
    monkeypatch.setattr(imageio_ffmpeg, 'count_frames_and_secs', check)
    if entry == 'probe_fps':
        assert provision.probe_fps('synthetic.webm') == 1
    elif entry == 'ffmpeg_exe':
        assert provision.ffmpeg_exe() == 'ffmpeg.exe'
    elif entry == 'thumbnail':
        assert not animation_thumbnail._decode_webm(Path('synthetic.webm')).isNull()
    elif entry == 'warm_exe':
        webm_clip._ensure_ffmpeg_exe()
        assert installed
    else:
        clip = webm_clip.WebMClip(str(tmp_path / 'synthetic.webm'))
        clip.warm_meta()
        assert clip._frame_count == 1


def test_non_ffmpeg_wrapper_keeps_original_flags(windows_spawn):
    webm_clip._PopenCapture._wrapped([sys.executable, '-c', 'pass'], creationflags=0x200)
    assert windows_spawn[0][0][1]['creationflags'] == 0x200


def test_positional_creationflags_are_merged_without_duplicate_keyword(windows_spawn, monkeypatch):
    assert list(inspect.signature(subprocess.Popen).parameters)[13] == 'creationflags'
    recorded = []
    monkeypatch.setattr(webm_clip._PopenCapture, '_real_popen',
                        lambda *args, **kwargs: recorded.append((args, kwargs)) or object())
    args = ('ffmpeg.exe', -1, None, None, None, None, None, True, False, None, None, None, None, 0x200)
    webm_clip._PopenCapture._wrapped(*args)
    assert recorded[0][0][13] == NO_WINDOW | 0x200
    assert 'creationflags' not in recorded[0][1]


def test_custom_sdk_executable_and_keyword_args_are_hidden(windows_spawn):
    imageio_ffmpeg._io.subprocess.Popen(args=['renamed-video-tool.exe', '-version'])
    assert windows_spawn[0][0][1]['creationflags'] == NO_WINDOW


def test_capture_is_nested_and_thread_local(windows_spawn):
    results = []
    barrier = threading.Barrier(3)

    def worker():
        with webm_clip._PopenCapture() as outer:
            first = imageio_ffmpeg._io.subprocess.Popen(['ffmpeg.exe'])
            barrier.wait(timeout=30)
            with webm_clip._PopenCapture() as inner:
                second = imageio_ffmpeg._utils.subprocess.Popen(['ffmpeg.exe'])
            third = imageio_ffmpeg._io.subprocess.Popen(['ffmpeg.exe'])
        results.append((outer._procs, inner._procs, [first, third], [second]))

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
        assert not thread.is_alive()
    assert len(results) == 3
    for outer, inner, expected_outer, expected_inner in results:
        assert outer == expected_outer and inner == expected_inner


@pytest.mark.parametrize('entry', ['check_call', 'check_output', 'run'])
@pytest.mark.parametrize('module', ['_io', '_utils'])
def test_scoped_stdlib_helpers_keep_real_output_errors_and_timeout(module, entry):
    webm_clip._PopenCapture._install()
    helper = getattr(getattr(imageio_ffmpeg, module).subprocess, entry)
    options = {'timeout': 30}
    if entry == 'check_call':
        assert helper([sys.executable, '-c', 'pass'], **options) == 0
    elif entry == 'check_output':
        assert helper([sys.executable, '-c', 'print("synthetic")'], **options).strip() == b'synthetic'
    else:
        assert helper([sys.executable, '-c', 'print("synthetic")'], capture_output=True,
                      text=True, check=True, **options).stdout.strip() == 'synthetic'
    with pytest.raises(subprocess.CalledProcessError) as failed:
        helper([sys.executable, '-c', 'raise SystemExit(7)'],
               **({'check': True} if entry == 'run' else {}), **options)
    assert failed.value.returncode == 7
    with webm_clip._PopenCapture() as capture:
        with pytest.raises(subprocess.TimeoutExpired):
            helper([sys.executable, '-c', 'import time; time.sleep(60)'], timeout=0.1)
    assert capture.process.poll() is not None


@pytest.mark.parametrize('entry', ['probe_fps', 'ffmpeg_exe', 'thumbnail', 'warm_exe'])
def test_session_end_does_not_install_or_spawn(monkeypatch, entry):
    monkeypatch.setattr(webm_clip, '_SESSION_ENDING', True)
    monkeypatch.setattr(webm_clip._PopenCapture, '_install', lambda: pytest.fail('installed after session end'))
    if entry == 'probe_fps':
        assert provision.probe_fps('synthetic.webm') == provision.DEFAULT_FPS
    elif entry == 'ffmpeg_exe':
        assert provision.ffmpeg_exe() is None
    elif entry == 'thumbnail':
        assert animation_thumbnail._decode_webm(Path('synthetic.webm')).isNull()
    else:
        webm_clip._ensure_ffmpeg_exe()
