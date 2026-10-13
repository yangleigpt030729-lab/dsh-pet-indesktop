"""Real Windows kernel/FFmpeg tests. Source paths do not certify a packaged EXE."""
import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import imageio_ffmpeg
import pytest
from PySide6.QtWidgets import QApplication

from pet import animation_thumbnail, frameseq_provision as provision, webm_clip

pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason='native Windows console/kernel required')
ROOT = Path(__file__).resolve().parents[1]

# This diagnostic starts without a console. AttachConsole succeeds if the
# FFmpeg process has one (even if STARTUPINFO merely hid its window).
_CONSOLE_PROBE = r'''
import ctypes, json, sys
k = ctypes.WinDLL('kernel32', use_last_error=True)
k.AttachConsole.argtypes = [ctypes.c_uint32]
k.AttachConsole.restype = ctypes.c_int
attached = bool(k.AttachConsole(int(sys.argv[1])))
print(json.dumps({'attached': attached, 'error': ctypes.get_last_error()}))
'''


@pytest.mark.parametrize('entry', ['version', 'metadata', 'first_frame', 'reader_restart',
                                  'fps', 'thumbnail', 'background_conversion'])
def test_real_spawn_has_no_console_outputs_frames_and_exits(monkeypatch, tmp_path, entry):
    app = QApplication.instance() or QApplication([])
    webm_clip._PopenCapture._install()
    real = webm_clip._PopenCapture._real_popen
    processes = []

    def observe(*args, **kwargs):
        assert kwargs['creationflags'] & subprocess.CREATE_NO_WINDOW
        proc = real(*args, **kwargs)
        processes.append(proc)
        if proc.poll() is None:
            probe = subprocess.run([sys.executable, '-c', _CONSOLE_PROBE, str(proc.pid)],
                                   capture_output=True, text=True, timeout=30,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
            assert probe.returncode == 0, probe.stderr
            result = json.loads(probe.stdout)
            assert not result['attached'], f'FFmpeg has a console: {proc.pid}'
            assert result['error'] == 6 or (result['error'] == 87 and proc.poll() is not None), result
        return proc

    monkeypatch.setattr(webm_clip._PopenCapture, '_real_popen', observe)
    original = min((ROOT / 'assets/characters/shenshen/videos').rglob('*.webm'),
                   key=lambda p: p.stat().st_size)
    sample = tmp_path / 'synthetic-acceptance.webm'
    shutil.copyfile(original, sample)  # independent caches; never alter shipped assets
    clip = webm_clip.WebMClip(sample)
    try:
        if entry == 'version':
            assert imageio_ffmpeg._utils._is_valid_exe(imageio_ffmpeg.get_ffmpeg_exe())
        elif entry == 'metadata':
            clip.warm_meta()
            assert clip._frame_count > 0 and clip._duration > 0
        elif entry == 'first_frame':
            image = clip._decode_first_qimage()
            assert image is not None and not image.isNull() and image.hasAlphaChannel()
            reader = imageio_ffmpeg.read_frames(str(sample), pix_fmt='rgba', bits_per_pixel=32,
                                               input_params=list(webm_clip._FFMPEG_INPUT_PARAMS))
            try:
                next(reader)
                assert bytes(image.constBits()) == next(reader)
            finally:
                reader.close()
        elif entry == 'reader_restart':
            for _ in range(3):
                frame = threading.Event()
                callback = lambda _index: frame.set()
                clip.frameChanged.connect(callback)
                clip.start()
                deadline = time.monotonic() + 30
                while not frame.is_set() and time.monotonic() < deadline:
                    app.processEvents()
                    frame.wait(0.01)
                assert frame.is_set(), 'reader did not deliver a Qt frame'
                clip.stop()
                clip.frameChanged.disconnect(callback)
        elif entry == 'fps':
            assert provision.probe_fps(sample) > 0
        elif entry == 'thumbnail':
            assert not animation_thumbnail._decode_webm(sample).isNull()
        else:
            target = provision.clip_out_dir(sample, tmp_path, tmp_path / 'frames')
            converted, problem = provision.convert_clip(sample, target)
            assert converted and not problem, problem
            assert list(target.glob('*.webp'))
        assert processes, 'test bypassed all actual FFmpeg creation'
    finally:
        clip.cleanup()
        for proc in processes:
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=30)
                pytest.fail(f'FFmpeg did not exit through original cleanup: {proc.pid}')
    assert all(proc.poll() is not None for proc in processes)
