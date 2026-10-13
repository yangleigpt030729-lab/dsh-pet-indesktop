"""Measure real Qt receipts/guards with only the audio boundary recorded offline."""
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psutil
from pet.companion.head_speech import speak_target
from tests.test_companion_feed_presentation import hosted
from tests.test_companion_head_speech import set_target_config


if __name__ == '__main__':
    results = []
    process = psutil.Process()
    before = process.memory_info().rss
    with tempfile.TemporaryDirectory(prefix='companion-speech-benchmark-') as directory:
        for topology in ('legacy', 'overlay'):
            for child in (False, True):
                with hosted(Path(directory)/f'{topology}-{child}', topology, child) as h:
                    set_target_config(h, 'self_talk_speak_enabled', True)
                    set_target_config(h, 'proactive_bubble_speak_enabled', True)
                    guards = []
                    h.host.on_self_talk_speak = lambda text, *, valid, config: guards.__setitem__(slice(None), [valid])
                    for active in (False, True):
                        enqueue, validate, rss = [], [], []
                        for n in range(200):
                            assert h.target.present(f'合成基准文字 {n}')
                            start = time.perf_counter_ns()
                            speak_target(h.target, h.bubble._raw_text, lambda: True, active=active)
                            enqueue.append((time.perf_counter_ns()-start)/1000)
                            guard = guards[-1]
                            for _ in range(10):
                                start = time.perf_counter_ns()
                                assert guard()
                                validate.append((time.perf_counter_ns()-start)/1000)
                            rss.append(process.memory_info().rss/1024**2)
                        results.append(dict(topology=topology, child=child, active=active,
                            receipts=len(enqueue), validations=len(validate),
                            rss_warm_mib=rss[19], rss_last_mib=rss[-1],
                            enqueue_mean_us=statistics.mean(enqueue), enqueue_max_us=max(enqueue),
                            validation_mean_us=statistics.mean(validate), validation_max_us=max(validate)))
                    assert h.shell.voice_chime_service is None
    print(json.dumps(dict(results=results, rss_before_mib=before/1024**2,
        rss_after_mib=process.memory_info().rss/1024**2, real_network_calls=0,
        audio_boundary='recorded; real sound NOT TESTED'), ensure_ascii=False))
