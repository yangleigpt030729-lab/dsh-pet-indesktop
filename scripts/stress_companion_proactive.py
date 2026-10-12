"""Repeat the affected asynchronous family three times under four CPU burners."""
import multiprocessing
import subprocess
import sys
from pathlib import Path


def burn(stop):
    n = 7
    while not stop.is_set():
        for _ in range(10000):
            n = (n*1103515245+12345) & 0x7fffffff


if __name__ == '__main__':
    stop = multiprocessing.Event()
    hogs = [multiprocessing.Process(target=burn, args=(stop,)) for _ in range(4)]
    for worker in hogs:
        worker.start()
    try:
        for n in range(3):
            print(f'LOAD ROUND {n+1}: 4 CPU burners', flush=True)
            command = [sys.executable, '-m', 'pytest', '-q', 'tests/test_companion_proactive_hardening.py', 'tests/test_companion_proactive_service.py', 'tests/test_companion_proactive_network.py', 'tests/test_companion_proactive_ui.py', 'tests/test_companion_proactive_failures.py', 'tests/test_companion_proactive_state.py', 'tests/test_companion_proactive_schedule.py', 'tests/test_companion_recall_intent.py', 'tests/test_companion_chat.py', 'tests/test_chat_service.py']
            command += ['tests/test_companion_settings_entry.py', 'tests/test_companion_acceptance_launcher.py']
            result = subprocess.run(command, cwd=Path(__file__).resolve().parents[1])
            if result.returncode:
                sys.exit(result.returncode)
    finally:
        stop.set()
        for worker in hogs:
            worker.join(10)
