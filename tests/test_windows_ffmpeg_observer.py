"""Safety of the external EXE observer; Win32 window sampling requires Windows."""
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest

from scripts import watch_windows_ffmpeg_console as observer

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(sys.platform == 'win32', reason='Linux rejection test')
def test_non_windows_cannot_generate_native_pass_report(tmp_path):
    data = tmp_path / 'data'
    report = tmp_path / 'report.json'
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/watch_windows_ffmpeg_console.py'),
                             '--exe', 'unused.exe', '--data-dir', str(data), '--report', str(report)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert 'native Windows required' in result.stderr
    assert not data.exists() and not report.exists()


def test_observer_ignores_pid_reuse_and_gone_processes(monkeypatch):
    def process(pid):
        if pid == 3:
            raise psutil.NoSuchProcess(pid)
        return SimpleNamespace(create_time=lambda: 123, is_running=lambda: True)

    monkeypatch.setattr(observer.psutil, 'Process', process)
    assert observer.surviving_children({1: 123, 2: 122, 3: 123}) == [1]


@pytest.mark.parametrize('existing', ['data', 'report'])
def test_existing_data_or_report_refused_before_launch(monkeypatch, tmp_path, existing):
    exe = tmp_path / 'portable/dsh-pet-standalone-webm-chat.exe'
    exe.parent.mkdir()
    exe.write_bytes(b'test')
    binaries = exe.parent / '_internal/imageio_ffmpeg/binaries'
    binaries.mkdir(parents=True)
    (binaries / 'ffmpeg-test.exe').write_bytes(b'test')
    data = tmp_path / 'data'
    report = tmp_path / 'report.json'
    if existing == 'data':
        data.mkdir()
        (data / 'keep.txt').write_text('keep')
    else:
        report.write_text('keep')
    monkeypatch.setattr(observer, 'sys', SimpleNamespace(platform='win32'))
    monkeypatch.setattr(sys, 'argv', ['watch', '--exe', str(exe), '--data-dir', str(data),
                                    '--report', str(report)])
    monkeypatch.setattr(observer.subprocess, 'Popen', lambda *_a, **_kw: pytest.fail('unexpected launch'))
    with pytest.raises(SystemExit):
        observer.main()
    assert ((data / 'keep.txt') if existing == 'data' else report).read_text() == 'keep'
