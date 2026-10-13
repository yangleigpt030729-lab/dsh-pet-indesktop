"""Real FFmpeg runtime and spawn-policy CPU benchmark (Git baseline required)."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tracemalloc
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtWidgets import QApplication
from PIL import Image
import imageio_ffmpeg
from pet import webm_clip as w, frameseq_provision as f, animation_thumbnail as t

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default='c0c2c11')
    args = parser.parse_args()
    app = QApplication.instance() or QApplication([])
    tracemalloc.start()
    before = tracemalloc.get_traced_memory()[0]
    start = time.perf_counter_ns()
    w._PopenCapture._install()
    install_ns = time.perf_counter_ns() - start
    retained = tracemalloc.get_traced_memory()[0] - before
    tracemalloc.stop()
    result = {'platform': sys.platform, 'python': sys.version.split()[0],
              'install_us': install_ns / 1000, 'install_retained_bytes': retained,
              'real_runtime': {}}
    real = w._PopenCapture._real_popen
    processes = []
    def spawn(*args, **kwargs):
        p = real(*args, **kwargs)
        processes.append(p)
        return p
    w._PopenCapture._real_popen = spawn
    sample = min((ROOT / 'assets/characters/shenshen/videos').rglob('*.webm'), key=lambda p:p.stat().st_size)
    def timed(name, func):
        start = time.perf_counter_ns()
        v = func()
        result['real_runtime'][name] = {'ms': (time.perf_counter_ns() - start)/1e6}
        return v
    with tempfile.TemporaryDirectory(prefix='ffmpeg-runtime-') as td:
        sample_copy = Path(td)/'acceptance.webm'
        shutil.copyfile(sample, sample_copy)
        clip = w.WebMClip(sample_copy)
        try:
            assert timed('version', lambda:imageio_ffmpeg._utils._is_valid_exe(f.ffmpeg_exe()))
            timed('metadata', clip.warm_meta)
            result['real_runtime']['metadata'].update(frames=clip._frame_count, fps=clip._fps)
            image = timed('first_frame', clip._decode_first_qimage)
            assert image and not image.isNull()
            pixels = bytes(image.constBits())
            alpha = Image.frombytes('RGBA', (image.width(),image.height()), pixels).getchannel('A').getextrema()
            gen = imageio_ffmpeg.read_frames(str(sample_copy), pix_fmt='rgba', bits_per_pixel=32,
                                           input_params=list(w._FFMPEG_INPUT_PARAMS))
            try:
                next(gen)
                reference = next(gen)
            finally:
                gen.close()
            assert pixels == reference
            result['real_runtime']['first_frame'].update(size=[image.width(),image.height()],
                    alpha=alpha, sha256=hashlib.sha256(pixels).hexdigest(), original_sdk_pixels_equal=True)
            assert timed('fps', lambda:f.probe_fps(sample_copy)) > 0
            assert not timed('thumbnail', lambda:t._decode_webm(sample_copy)).isNull()
            for n in range(3):
                event = threading.Event()
                def frame(i): event.set()
                clip.frameChanged.connect(frame)
                start = time.perf_counter_ns()
                clip.start()
                deadline = time.monotonic()+30
                while not event.is_set() and time.monotonic()<deadline:
                    app.processEvents()
                    event.wait(.01)
                assert event.is_set()
                result['real_runtime'][f'reader_restart_{n}'] = {'first_delivery_ms': (time.perf_counter_ns()-start)/1e6}
                clip.stop()
                clip.frameChanged.disconnect(frame)
            target = f.clip_out_dir(sample_copy, Path(td), Path(td)/'frames')
            converted, problem = timed('conversion', lambda:f.convert_clip(sample_copy, target))
            assert converted and not problem, problem
            result['real_runtime']['conversion']['frame_files'] = len(list(target.glob('*.webp')))
        finally:
            clip.cleanup()
            for p in processes:
                p.wait(timeout=30)
        assert all(p.poll() is not None for p in processes)
    result['real_runtime']['all_processes_exited'] = len(processes)
    w._PopenCapture._real_popen = real

    # Compare baseline vs repaired wrapper at an OS boundary recorder. This is
    # a process-policy CPU benchmark, not a fabricated Windows runtime measurement.
    old_src = subprocess.check_output(['git','show',args.baseline+':pet/webm_clip.py'],text=True, cwd=ROOT)
    tree = ast.parse(old_src)
    node = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='_PopenCapture')
    space = dict(w.__dict__)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<baseline>', 'exec'),space)
    old = space['_PopenCapture']
    orig_os, orig_job = w.os, w.win_job
    w.os = SimpleNamespace(name='nt')
    w.win_job = SimpleNamespace(adopt=lambda p:None)
    space['win_job'] = w.win_job
    space['os'] = w.os
    dummy = object()
    for cls in (old,w._PopenCapture):
        cls._real_popen = lambda *args,**kwargs:dummy
    argv = [r'D:\app\ffmpeg-win-x86_64-v7.1.exe','-version']
    for name,cls in (('baseline',old),('patched',w._PopenCapture)):
        rounds=[]
        for _ in range(3):
            begin=time.perf_counter_ns()
            for _ in range(100000): cls._wrapped(argv,creationflags=0x200)
            rounds.append((time.perf_counter_ns()-begin)/100000/1000)
        result[name+'_wrapper_us_per_spawn'] = rounds
    w.os, w.win_job = orig_os, orig_job
    w._PopenCapture._real_popen = real
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
