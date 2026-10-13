"""Deterministic latency boundaries; network/audio are synthetic."""
import threading
import time
from pathlib import Path

from pet import voice_chime_service as speech
from tests.test_companion_interactions import setup
from tests.test_companion_proactive_service import FakeProvider


def test_voice_synthesis_never_waits_for_voice_list(tmp_path, monkeypatch):
    release, done = threading.Event(), threading.Event()
    monkeypatch.setattr(speech, 'refresh_voice_list', lambda **kw: release.wait(15))
    async def synth(worker, voice):
        worker._out_path.write_bytes(b'synthetic audio')
    monkeypatch.setattr(speech._TTSWorker, '_synthesize', synth)
    worker = speech._TTSWorker('合成低延迟测试', speech.DEFAULT_VOICE, '+0%', '+0Hz', tmp_path/'audio.mp3', lambda *_: done.set())
    try:
        worker.start()
        assert done.wait(2), 'voice list refresh blocked synthesis'
    finally:
        release.set()
        worker.join(20)
        assert not worker.is_alive()


def test_feed_starts_without_advancing_a_two_second_clock(tmp_path):
    provider = FakeProvider(['合成零食已经收到啦。'])
    app, cfg, target, service = setup(tmp_path, provider)
    service.clock = lambda: 100.0  # A fixed clock must not need +2s to release a feed.
    started = time.monotonic()
    try:
        for _ in range(12):
            service.offer_feeding(target, {'categories': {'python': 1}, 'files': 1})
        deadline = started+2
        while not provider.calls and time.monotonic() < deadline:
            app.processEvents()
            threading.Event().wait(.001)
        assert len(provider.calls) == 1
        assert '"python": 12' in str(provider.calls)
    finally:
        service.close()


def test_default_menu_registers_volume_control(tmp_path):
    from PySide6.QtWidgets import QApplication, QMenu
    from pet.context_menus.registry import MENU_ACTIONS
    from pet.config import Config
    from types import SimpleNamespace
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    menu = QMenu()
    try:
        MENU_ACTIONS.populate(menu, SimpleNamespace(cfg=cfg), [{'type':'action','id':'voice_volume','visible':True}])
        assert any(a.text() == '音量控制' and a.menu() is not None for a in menu.actions())
        assert app is not None
    finally:
        menu.close()
        menu.deleteLater()


def test_voice_table_refresh_is_single_flight_and_failure_throttled(monkeypatch):
    release, started = threading.Event(), threading.Event()
    calls = []
    def refresh(**kw):
        calls.append(kw)
        started.set()
        release.wait(10)
    monkeypatch.setattr(speech, '_live_voices', None)
    monkeypatch.setattr(speech, '_refresh_attempt_at', float('-inf'))
    monkeypatch.setattr(speech, '_refresh_thread', None)
    monkeypatch.setattr(speech, 'refresh_voice_list', refresh)
    try:
        assert speech.request_voice_refresh()
        assert started.wait(5)
        assert not speech.request_voice_refresh()
        release.set()
        speech._refresh_thread.join(15)
        assert not speech._refresh_thread.is_alive()
        assert not speech.request_voice_refresh()
        assert calls == [{'timeout': speech.VOICE_REFRESH_TIMEOUT_S}]
    finally:
        release.set()
        speech._refresh_thread.join(15)


def test_cancelled_refresh_bridge_does_not_start_network(tmp_path, monkeypatch):
    from tests.test_voice_chime_service import _service
    from tests.test_companion_chat import wait
    from PySide6.QtWidgets import QApplication
    service, _, _ = _service(tmp_path, monkeypatch)
    service._stopped = False
    calls = []
    monkeypatch.setattr(speech, 'request_voice_refresh', lambda: calls.append('network'))
    bridge = speech._AudioBridge()
    bridge.signals.refresh_requested.connect(service._refresh_voices)
    allowed = [True]
    t = threading.Thread(target=lambda: bridge.on_refresh(lambda: allowed[0]))
    t.start()
    t.join(5)
    allowed[0] = False
    QApplication.instance().processEvents()
    assert calls == []
    service.stop()
    # No network is scheduled by an already stopped service either.
    bridge.on_refresh(None)
    wait(QApplication.instance(), lambda: not calls)


def test_fake_acceptance_never_starts_live_voice_metadata(tmp_path, monkeypatch):
    from tests.test_companion_acceptance_launcher import installed_fake
    from tests.test_companion_feed_presentation import hosted
    from tests.test_companion_head_speech import set_target_config
    from pet.companion.head_speech import speak_target
    installed_fake.__wrapped__(monkeypatch)
    def forbidden(*a, **kw):
        raise AssertionError('Fake initiated voice metadata network')
    monkeypatch.setattr(speech, 'request_voice_refresh', forbidden)
    with hosted(tmp_path, 'overlay') as h:
        set_target_config(h, 'self_talk_speak_enabled', True)
        assert h.target.present('合成离线语音')
        speak_target(h.target, h.bubble._raw_text, lambda: True)
        assert h.shell.voice_chime_service._acceptance_speech == [h.bubble._raw_text]


def test_actual_feed_pipeline_records_request_reply_and_speech_stages():
    from scripts.benchmark_companion_latency import run
    measured = run(samples=1)
    assert measured['real_network_calls'] == 0
    assert len(measured['samples']) == 4
    for row in measured['samples']:
        assert row['model_calls'] == row['synthesis_calls'] == 1
        assert 0 <= row['drop_to_stats_ms'] <= row['drop_to_reply_ms']
        assert row['drop_to_reply_ms'] <= row['drop_to_play_call_ms']
        assert {'feed_to_request', 'feed_to_reply'} <= {s for s, ms in row['feeding_timings']}
        assert {'cache_miss', 'synthesis_total', 'play_request'} <= {s for s, ms in row['speech_timings']}
