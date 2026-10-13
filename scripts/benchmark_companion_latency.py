"""Measure real Qt drop/stats/model/receipt stages; only provider/audio are synthetic."""
import json
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pytest import MonkeyPatch
from tests.test_companion_feed_presentation import hosted
from tests.test_companion_head_speech import set_target_config
from tests.test_companion_chat import wait
from tests.test_companion_proactive_service import FakeProvider
from tests.test_voice_chime_service import _service, _WorkerSpy
from pet.companion.interaction_service import InteractionService


def run(samples=3):
    rows = []
    with tempfile.TemporaryDirectory(prefix='speech-latency-benchmark-') as root:
        for topology in ('legacy', 'overlay'):
            for child in (False, True):
                for number in range(samples):
                    patch = MonkeyPatch()
                    directory = Path(root)/f'{topology}-{child}-{number}'
                    directory.mkdir()
                    try:
                        with hosted(directory, topology, child) as h:
                            channel, _, _ = _service(directory/'voice', patch)
                            h.shell.voice_chime_service = channel
                            set_target_config(h, 'self_talk_speak_enabled', True)
                            provider = FakeProvider([f'合成趣味零食回复第{number}份。'])
                            service = h.shell.companion_interactions = InteractionService(provider=provider)
                            stage = {}
                            service.delivered.connect(lambda kind, text: stage.update(reply=time.monotonic()))
                            path = directory/'synthetic.png'
                            path.write_bytes(b'SYNTHETIC UNREAD FILE BYTES')
                            start = time.monotonic()
                            h.drop([str(path)])
                            wait(h.app, lambda: not h.worker.feed_busy)
                            stats = time.monotonic()
                            wait(h.app, lambda: len(provider.calls) == 1)
                            request = time.monotonic()
                            wait(h.app, lambda: bool(stage) and len(_WorkerSpy.instances) == 1)
                            worker = _WorkerSpy.instances[0]
                            assert worker.text == h.bubble._raw_text  # stats never speaks
                            worker.out_path.write_bytes(b'synthetic MP3')
                            worker.finish()
                            wait(h.app, lambda: channel._player.plays == 1)
                            played = time.monotonic()
                            assert path.read_bytes() == b'SYNTHETIC UNREAD FILE BYTES'
                            rows.append(dict(topology=topology, child=child,
                                drop_to_stats_ms=(stats-start)*1000,
                                drop_to_provider_ms=(request-start)*1000,
                                drop_to_reply_ms=(stage['reply']-start)*1000,
                                reply_to_play_call_ms=(played-stage['reply'])*1000,
                                drop_to_play_call_ms=(played-start)*1000,
                                model_calls=len(provider.calls), synthesis_calls=len(_WorkerSpy.instances),
                                feeding_timings=list(getattr(service, 'timings', ())), speech_timings=list(channel.timings)))
                    finally:
                        patch.undo()
    return dict(samples=rows, real_network_calls=0, sound='synthetic playback invocation; Windows real sound NOT TESTED')


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False))
