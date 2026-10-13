"""Repeat the persona/chat request family under four CPU burners, three rounds."""
import multiprocessing
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.stress_companion_proactive import burn


if __name__ == '__main__':
    stop = multiprocessing.Event()
    workers = [multiprocessing.Process(target=burn, args=(stop,)) for _ in range(4)]
    for worker in workers:
        worker.start()
    try:
        for number in range(3):
            print(f'PERSONA LOAD ROUND {number+1}: 4 CPU burners', flush=True)
            subprocess.run([sys.executable, '-m', 'pytest', '-q',
                'tests/test_chat_persona_priority.py', 'tests/test_chat_service.py',
                'tests/test_chat_safe_emit.py', 'tests/test_companion_expression.py',
                'tests/test_companion_interactions.py', 'tests/test_companion_proactive_service.py',
                'tests/test_companion_chat.py', 'tests/test_companion_head_speech.py'],
                cwd=Path(__file__).resolve().parents[1], check=True)
    finally:
        stop.set()
        for worker in workers:
            worker.join(10)
