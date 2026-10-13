"""Launch one isolated Fake EXE and record console/exit evidence on Windows.

This diagnostic samples visible windows, not every Win32 window-creation event.
Interaction scenarios remain manual; it never opens credentials or media files.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil


def visible_ffmpeg_windows(binary_dir):
    user = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.EnumWindows.restype = wintypes.BOOL
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.IsWindowVisible.restype = wintypes.BOOL
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetWindowTextW.restype = ctypes.c_int
    result = []
    binaries = [str(path.resolve()).casefold() for path in binary_dir.glob('ffmpeg*.exe')]

    def visit(hwnd, _param):
        if user.IsWindowVisible(hwnd):
            title = ctypes.create_unicode_buffer(4096)
            user.GetWindowTextW(hwnd, title, len(title))
            if any(binary in title.value.casefold() for binary in binaries):
                # Do not record other window titles, paths or private content.
                result.append({'hwnd': int(hwnd), 'binary': 'bundled-ffmpeg'})
        return True

    callback = callback_type(visit)
    if not user.EnumWindows(callback, 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return result


def surviving_children(children):
    survivors = []
    for pid, born in children.items():
        try:
            proc = psutil.Process(pid)
            if proc.create_time() == born and proc.is_running():
                survivors.append(pid)
        except psutil.NoSuchProcess:
            pass
    return survivors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', required=True, type=Path)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--seconds', type=int, default=900)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('native Windows required; Linux cannot certify an EXE')
    exe = args.exe.resolve(strict=True)
    if exe.name != 'dsh-pet-standalone-webm-chat.exe':
        parser.error('select the reviewed Chat onedir EXE')
    binary_dir = exe.parent / '_internal/imageio_ffmpeg/binaries'
    if not list(binary_dir.glob('ffmpeg*.exe')):
        parser.error('bundled FFmpeg missing; extract the complete portable ZIP')
    if args.data_dir.exists() or args.report.exists() or args.seconds < 1:
        parser.error('use NEW external data/report paths and a positive duration')
    data_dir = args.data_dir.resolve()
    if data_dir == exe.parent or exe.parent in data_dir.parents:
        parser.error('data-dir must be outside the portable folder')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop('QT_QPA_PLATFORM', None)
    proc = subprocess.Popen([str(exe), '--companion-acceptance', '--data-dir', str(data_dir)],
                            cwd=exe.parent, env=env, creationflags=subprocess.CREATE_NO_WINDOW,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    children = {}
    windows = {}
    errors = []
    deadline = time.monotonic() + args.seconds
    print('Fake EXE started. Test startup/assets/head/feed/recycling; exit from the tray when done.', flush=True)
    try:
        while proc.poll() is None and time.monotonic() < deadline:
            try:
                for child in psutil.Process(proc.pid).children(recursive=True):
                    if child.name().lower().startswith('ffmpeg'):
                        children[child.pid] = child.create_time()
            except psutil.NoSuchProcess:
                pass
            for found in visible_ffmpeg_windows(binary_dir):
                windows.setdefault(found['hwnd'], found)
            time.sleep(0.05)
    except (KeyboardInterrupt, OSError, psutil.Error) as exc:
        errors.append(type(exc).__name__)
    # Do not kill an existing pet or the user's old portable instance. If this
    # observer times out, its own EXE stays running for manual tray exit.
    normal_exit = proc.poll() is not None and proc.returncode == 0
    survivors = surviving_children(children) if proc.poll() is not None else []
    orphan_deadline = time.monotonic() + 10
    while survivors and time.monotonic() < orphan_deadline:
        time.sleep(0.05)
        survivors = surviving_children(children)
    report = {'mode': 'Windows native EXE / isolated Fake',
              'console_sampling_ms': 50, 'visible_ffmpeg_windows': list(windows.values()),
              'observed_ffmpeg_processes': len(children),
              'console_observation': ('FAIL' if windows or errors else
                                      'PASS' if children else 'NOT TESTED'),
              'normal_exit': 'PASS' if normal_exit else 'NOT TESTED',
              'orphans': survivors,
              'orphan_observation': ('FAIL' if survivors else 'PASS') if normal_exit else 'NOT TESTED',
              'errors': errors,
              'manual_scenarios': 'Record startup/assets/head/feed/meta/first-frame/conversion/recycle separately.',
              'limitations': 'Sampling may miss very short flashes; no automatic GUI/frame or audio certification.'}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Report: {args.report}', flush=True)
    print(f"Console: {report['console_observation']}; exit: {report['normal_exit']}; orphans: {report['orphan_observation']}")
    if not normal_exit:
        print('Exit this test pet from the tray; rerun with fresh paths for complete exit/orphan evidence.')
    return 1 if windows or survivors or errors or not normal_exit or not children else 0


if __name__ == '__main__':
    raise SystemExit(main())
