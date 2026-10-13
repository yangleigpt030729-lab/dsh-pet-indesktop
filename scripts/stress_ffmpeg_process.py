"""Run affected spawn/lifecycle families three times with four CPU burners."""
import multiprocessing
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.stress_companion_proactive import burn

if __name__ == '__main__':
    stop = multiprocessing.Event()
    hogs = [multiprocessing.Process(target=burn, args=(stop,)) for _ in range(4)]
    for hog in hogs:
        hog.start()
    groups = [
        ['tests/test_ffmpeg_console_flags.py', 'tests/test_session_end_ffmpeg_guard.py',
         'tests/test_frameseq_provision.py', 'tests/test_animation_thumbnail_cache.py'],
        ['tests/test_webm_reader_lifecycle.py', 'tests/test_webm_clip_lifecycle.py',
         'tests/test_webm_first_frame_lock.py'],
        ['tests/test_low_priority_warm_interaction_yield.py'],
    ]
    try:
        for n in range(3):
            print(f'ROUND {n+1} / 4 CPU burners', flush=True)
            for group in groups:
                result = subprocess.run([sys.executable, '-m', 'pytest', '-q', *group],
                                        cwd=ROOT)
                if result.returncode:
                    sys.exit(result.returncode)
    finally:
        stop.set()
        for hog in hogs:
            hog.join(30)
