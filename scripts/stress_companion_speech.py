"""Run the affected interaction/speech/todo timing family under four CPU burners."""
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
            print(f'COMPANION SPEECH ROUND {number+1}: 4 CPU burners', flush=True)
            subprocess.run([sys.executable, '-m', 'pytest', '-q',
                'tests/test_companion_dual_speech.py', 'tests/test_companion_head_speech.py',
                'tests/test_voice_chime_service.py', 'tests/test_todo_delivery.py',
                'tests/test_companion_proactive_service.py', 'tests/test_companion_interactions.py',
                'tests/test_companion_result_speech.py', 'tests/test_island_overlay_chat_entry.py',
                'tests/test_edge_tts_endpoint.py', 'tests/test_file_interpret.py',
                'tests/test_single_process_shared.py',
                'tests/test_companion_latency.py', 'tests/test_companion_volume.py',
                'tests/test_companion_precue_speech.py', 'tests/test_menu_layout.py',
                'tests/test_sprite_menu_facade.py', 'tests/test_sprite_menu_parity.py',
                'tests/test_proactive.py', 'tests/test_overlay_chat_proactive.py',
                'tests/test_overlay_self_talk.py', 'tests/test_click_self_talk_speech.py'],
                cwd=Path(__file__).resolve().parents[1], check=True)
    finally:
        stop.set()
        for worker in workers:
            worker.join(10)
