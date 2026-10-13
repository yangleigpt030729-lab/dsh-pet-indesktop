"""Real frame-ready business boundary; screenshot/network/audio are synthetic."""
import threading
import pytest
from pet.proactive import ProactiveScreenWatcher
from pet.multi_window_shared import MultiWindowProxy
from tests.test_companion_feed_presentation import hosted
from tests.test_companion_head_speech import set_target_config
from tests.test_companion_chat import wait
from tests.test_companion_acceptance_launcher import installed_fake as _fake_fixture


@pytest.fixture
def installed_fake(monkeypatch):
    return _fake_fixture.__wrapped__(monkeypatch)


def trigger(h, monkeypatch, *, pre_cue=True, active=True):
    from pet import vision
    h.cfg.set('proactive_chat', {'enabled': False})
    h.cfg.set('proactive_screen', {'enabled': True, 'pre_cue': pre_cue, 'whitelist': ['*']})
    set_target_config(h, 'proactive_bubble_speak_enabled', active)
    release, started = threading.Event(), threading.Event()
    def response(*a, **k):
        started.set()
        release.wait(30)
        return '合成最终识屏回复。'
    monkeypatch.setattr(vision, '_post_vision_request', response)
    from pet.overlay_shell import _SpritePetHost
    host = _SpritePetHost(h.host, h.target.sprite_ref()) if h.target.sprite_ref else MultiWindowProxy(h.shell)
    watcher = ProactiveScreenWatcher(host, h.cfg)
    watcher.limiter.dry_run = False
    watcher._on_frame_ready(b'synthetic jpeg', 'synthetic', 1, 123, {'_gen':watcher._generation})
    assert started.wait(10)
    return watcher, release


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('passive,active', [(False, False), (True, False), (False, True), (True, True)])
def test_actual_precue_only_reads_active_category(tmp_path, monkeypatch, installed_fake, topology, passive, active):
    with hosted(tmp_path, topology) as h:
        set_target_config(h, 'self_talk_speak_enabled', passive)
        watcher, release = trigger(h, monkeypatch, active=active)
        try:
            assert h.bubble._raw_text == '让我看看……'
            spoken = getattr(h.shell.voice_chime_service, '_acceptance_speech', [])
            assert spoken == (['让我看看……'] if active else [])
        finally:
            watcher.pause()
            release.set()
            wait(h.app, lambda: not watcher._worker_busy)
            h.app.processEvents()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('cancel', ['voice_off', 'screen_off', 'precue_off', 'hide', 'replace', 'task', 'expired', 'role'])
def test_precue_synthesis_revoked_before_play(tmp_path, monkeypatch, topology, cancel):
    from tests.test_voice_chime_service import _service, _WorkerSpy
    with hosted(tmp_path, topology) as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        h.shell.voice_chime_service = channel
        watcher, release = trigger(h, monkeypatch)
        try:
            wait(h.app, lambda: len(_WorkerSpy.instances) == 1)
            if cancel == 'voice_off':
                set_target_config(h, 'proactive_bubble_speak_enabled', False)
            elif cancel == 'screen_off':
                h.cfg.set('proactive_screen', {'enabled': False})
            elif cancel == 'precue_off':
                h.cfg.set('proactive_screen', {'enabled': True, 'pre_cue':False})
            elif cancel == 'hide' or cancel == 'expired':
                h.bubble.hide()  # actual timeout hides via the same Qt receipt boundary
            elif cancel == 'replace':
                assert h.target.present('较新的最终回复')
            elif cancel == 'task':
                watcher.pause()
            else:
                h.cfg.set('character', 'new-role')
            worker = _WorkerSpy.instances[0]
            worker.out_path.write_bytes(b'synthetic audio')
            worker.finish()
            wait(h.app, lambda: not channel._busy)
            assert channel._player.plays == 0
        finally:
            watcher.pause()
            release.set()
            wait(h.app, lambda: not watcher._worker_busy)
            h.app.processEvents()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
def test_precue_disabled_skips_prompt_speech(tmp_path, monkeypatch, installed_fake, topology):
    with hosted(tmp_path, topology) as h:
        before = h.bubble.text_presentation_id
        watcher, release = trigger(h, monkeypatch, pre_cue=False)
        try:
            assert h.bubble.text_presentation_id == before
            assert getattr(h.shell.voice_chime_service, '_acceptance_speech', []) == []
        finally:
            watcher.pause()
            release.set()
            wait(h.app, lambda: not watcher._worker_busy)
