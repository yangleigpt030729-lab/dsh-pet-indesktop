"""Real consent/reply/Qt receipt paths; network and audio are synthetic."""
import threading

import pytest

from pet.multi_window_shared import MultiWindowProxy
from pet.proactive import ProactiveScreenWatcher
from tests.test_companion_acceptance_launcher import installed_fake as _fake_fixture
from tests.test_companion_chat import wait
from tests.test_companion_feed_presentation import hosted
from tests.test_companion_head_speech import set_target_config


@pytest.fixture
def installed_fake(monkeypatch):
    return _fake_fixture.__wrapped__(monkeypatch)


def spoken(h):
    return getattr(h.shell.voice_chime_service, '_acceptance_speech', [])


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
@pytest.mark.parametrize('passive,active', [(False, False), (True, False), (False, True), (True, True)])
def test_file_consent_success_reads_only_displayed_completion(tmp_path, installed_fake, topology, child, passive, active):
    with hosted(tmp_path, topology, child) as h:
        set_target_config(h, 'file_interpret', {'enabled': True})
        set_target_config(h, 'self_talk_speak_enabled', passive)
        set_target_config(h, 'proactive_bubble_speak_enabled', active)
        path = tmp_path/'authorized.txt'
        path.write_text('SYNTHETIC AUTHORIZED CONTENT', encoding='utf-8')
        h.drop([str(path)])
        wait(h.app, lambda: not h.worker.feed_busy)
        assert h.ctrl._state == 'awaiting' and h.ctrl._service is None
        assert spoken(h) == []
        h.ctrl._on_confirm()
        assert spoken(h) == []  # started / progress never reads aloud
        h.ctrl._on_heartbeat()
        assert spoken(h) == []
        wait(h.app, lambda: h.ctrl._state == 'idle')
        assert h.bubble._raw_text.startswith('解读完成：')
        assert spoken(h) == ([h.bubble._raw_text] if passive else [])
        h.ctrl._on_finished('stale-request', 'stale result')
        assert len(spoken(h)) == int(passive)
        assert path.read_text(encoding='utf-8') == 'SYNTHETIC AUTHORIZED CONTENT'


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
@pytest.mark.parametrize('passive,active', [(False, False), (True, False), (False, True), (True, True)])
def test_screen_reply_uses_active_without_ordinary_proactive(tmp_path, monkeypatch, installed_fake, topology, child, passive, active):
    from pet import vision
    with hosted(tmp_path, topology, child) as h:
        set_target_config(h, 'self_talk_speak_enabled', passive)
        set_target_config(h, 'proactive_bubble_speak_enabled', active)
        h.cfg.set('proactive_chat', {'enabled': False})
        h.cfg.set('proactive_screen', {'enabled': True, 'whitelist': ['*']})
        # The shared overlay watcher presents to the primary actor. Exercise
        # the existing child presentation host separately, without inventing
        # a new broadcast policy for all sprites.
        from pet.overlay_shell import _SpritePetHost
        host = _SpritePetHost(h.host, h.target.sprite_ref()) if topology == 'overlay' and child else MultiWindowProxy(h.shell)
        watcher = ProactiveScreenWatcher(host, h.cfg)
        monkeypatch.setattr(vision, '_post_vision_request', lambda *a, **k: '合成识屏回复已经展示。')
        try:
            thread = threading.Thread(target=watcher._worker_request_vision,
                                      args=(b'synthetic-jpeg', 'synthetic', 'prompt', h.cfg.chat_settings().active_config),
                                      kwargs={'gen': watcher._generation})
            thread.start()
            thread.join(30)
            assert not thread.is_alive()
            wait(h.app, lambda: h.bubble._raw_text == '合成识屏回复已经展示。')
            assert spoken(h) == ([h.bubble._raw_text] if active else [])
        finally:
            watcher.pause()


def file_request(h, path):
    from pet.chat.service import ChatService
    from tests.test_companion_proactive_service import FakeProvider
    provider = FakeProvider(['文件里的合成内容已读完。'])
    provider.synthetic_acceptance = True
    h.ctrl._service_factory = lambda: ChatService(provider=provider)
    path.write_text('SYNTHETIC CONSENT CONTENT', encoding='utf-8')
    from pet.feed_presentation import OverlayInterpretTarget
    actor = OverlayInterpretTarget(h.host, h.target.sprite_ref()) if h.target.sprite_ref else None
    assert h.ctrl.offer([str(path)], target=actor)
    h.ctrl._on_confirm()
    return provider


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
@pytest.mark.parametrize('kind', ['file', 'screen'])
@pytest.mark.parametrize('cancel', ['speech_off', 'feature_off', 'role', 'hide', 'replaced', 'task', 'quit'])
def test_pending_reply_audio_revoked_before_original_player(tmp_path, monkeypatch, topology, child, kind, cancel):
    from pet import vision
    from tests.test_voice_chime_service import _service, _WorkerSpy
    with hosted(tmp_path, topology, child) as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        set_target_config(h, 'self_talk_speak_enabled', True)
        set_target_config(h, 'proactive_bubble_speak_enabled', True)
        set_target_config(h, 'file_interpret', {'enabled': True})
        h.cfg.set('proactive_screen', {'enabled': True, 'whitelist': ['*']})
        watcher = None
        try:
            if kind == 'file':
                file_request(h, tmp_path/'consented.txt')
                wait(h.app, lambda: h.ctrl._state == 'idle')
            else:
                from pet.overlay_shell import _SpritePetHost
                host = _SpritePetHost(h.host, h.target.sprite_ref()) if topology == 'overlay' and child else MultiWindowProxy(h.shell)
                watcher = ProactiveScreenWatcher(host, h.cfg)
                monkeypatch.setattr(vision, '_post_vision_request', lambda *a, **k: '已展示的合成识屏回复。')
                watcher._worker_request_vision(b'synthetic', '', '', h.cfg.chat_settings().active_config, gen=watcher._generation)
            wait(h.app, lambda: len(_WorkerSpy.instances) == 1)
            if cancel == 'speech_off':
                set_target_config(h, 'self_talk_speak_enabled' if kind == 'file' else 'proactive_bubble_speak_enabled', False)
            elif cancel == 'feature_off':
                set_target_config(h, 'file_interpret' if kind == 'file' else 'proactive_screen', {'enabled': False})
                if kind == 'screen':
                    h.cfg.set('proactive_screen', {'enabled': False})
            elif cancel == 'role':
                set_target_config(h, 'character', 'different-role')
            elif cancel == 'hide':
                h.bubble.hide()
            elif cancel == 'replaced':
                assert h.target.present('新的状态文字不朗读')
            elif cancel == 'task':
                if watcher:
                    watcher.pause()
                else:
                    h.ctrl.offer([str(tmp_path/'consented.txt')], target=h.ctrl._target)
            else:
                h.shell._quitting = True
            worker = _WorkerSpy.instances[0]
            worker.out_path.write_bytes(b'synthetic audio')
            worker.finish()
            wait(h.app, lambda: not channel._busy)
            assert channel._player.plays == 0
            assert not channel._queued_fire
        finally:
            if watcher:
                watcher.pause()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('kind', ['file', 'screen'])
def test_failure_and_status_bubbles_do_not_speak(tmp_path, monkeypatch, installed_fake, topology, kind):
    from pet import vision
    with hosted(tmp_path, topology) as h:
        set_target_config(h, 'self_talk_speak_enabled', True)
        set_target_config(h, 'proactive_bubble_speak_enabled', True)
        if kind == 'file':
            file_request(h, tmp_path/'consented.txt')
            rid = h.ctrl._request_id
            h.ctrl._on_error(rid, 'synthetic provider error')
            h.ctrl._on_finished(rid, 'late completion must not read aloud')
            assert spoken(h) == []
        else:
            h.cfg.set('proactive_screen', {'enabled': True})
            watcher = ProactiveScreenWatcher(MultiWindowProxy(h.shell), h.cfg)
            def failed(*_a, **_k):
                raise RuntimeError('synthetic provider failure')
            monkeypatch.setattr(vision, '_post_vision_request', failed)
            watcher._worker_request_vision(b'synthetic', '', '', h.cfg.chat_settings().active_config, gen=watcher._generation)
            watcher.pause()
        for text in ['让我看看……', '开始解读', '已读取 20 字 / 3 秒', '解读失败', '解读已停止',
                     'API 余额 100', '余额变化', 'Agent 消费统计', '累计吃掉 3 个文件']:
            h.host.show_bubble(text)
            assert spoken(h) == []


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
def test_screen_reply_queued_before_disable_is_discarded(tmp_path, monkeypatch, installed_fake, topology):
    from pet import vision
    with hosted(tmp_path, topology) as h:
        set_target_config(h, 'proactive_bubble_speak_enabled', True)
        h.cfg.set('proactive_screen', {'enabled': True})
        watcher = ProactiveScreenWatcher(MultiWindowProxy(h.shell), h.cfg)
        monkeypatch.setattr(vision, '_post_vision_request', lambda *a, **k: 'queued obsolete reply')
        before = h.bubble.text_presentation_id
        thread = threading.Thread(target=watcher._worker_request_vision,
            args=(b'synthetic', '', '', h.cfg.chat_settings().active_config), kwargs={'gen': watcher._generation})
        thread.start()
        thread.join(30)
        assert not thread.is_alive()
        watcher.pause()
        h.app.processEvents()
        assert h.bubble.text_presentation_id == before and spoken(h) == []


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('kind', ['file', 'screen'])
def test_suppressed_success_does_not_read_old_visible_text(tmp_path, monkeypatch, installed_fake, topology, kind):
    from pet import vision
    with hosted(tmp_path, topology) as h:
        set_target_config(h, 'self_talk_speak_enabled', True)
        set_target_config(h, 'proactive_bubble_speak_enabled', True)
        h.host.show_bubble('原来的状态气泡')
        if kind == 'file':
            file_request(h, tmp_path/'consented.txt')
            before = h.bubble.text_presentation_id
            h.host.set_bubble_suppressed(True)
            wait(h.app, lambda: h.ctrl._state == 'idle')
        else:
            before = h.bubble.text_presentation_id
            h.host.set_bubble_suppressed(True)
            h.cfg.set('proactive_screen', {'enabled': True})
            watcher = ProactiveScreenWatcher(MultiWindowProxy(h.shell), h.cfg)
            monkeypatch.setattr(vision, '_post_vision_request', lambda *a, **k: 'suppressed successful reply')
            watcher._worker_request_vision(b'synthetic', '', '', h.cfg.chat_settings().active_config, gen=watcher._generation)
            watcher.pause()
        assert h.bubble.text_presentation_id == before and spoken(h) == []


def test_reading_or_screen_alone_keeps_channel_without_other_consumers(tmp_path):
    from PySide6.QtWidgets import QApplication
    from pet.app import AppShell
    from pet.config import Config
    cfg = Config(base=tmp_path)
    cfg.set('todo_reminder_enabled', False)
    cfg.set('proactive_chat', {'enabled': False})
    cfg.set('companion_interaction', {'head_touch_enabled': False, 'feeding_enabled': False})
    cfg.set('self_talk_enabled', False)
    cfg.set('click_show_self_talk', False)
    shell = AppShell(QApplication.instance(), cfg)
    try:
        for kind in ('file', 'screen'):
            cfg.set('file_interpret', {'enabled': kind == 'file'})
            cfg.set('proactive_screen', {'enabled': kind == 'screen'})
            cfg.set('self_talk_speak_enabled', kind == 'file')
            cfg.set('proactive_bubble_speak_enabled', kind == 'screen')
            assert shell._self_talk_speak_wanted()
            cfg.set('self_talk_speak_enabled', False)
            cfg.set('proactive_bubble_speak_enabled', False)
            assert not shell._self_talk_speak_wanted()
    finally:
        shell._teardown_config_watcher()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
def test_voice_opt_in_never_reads_unconfirmed_file(tmp_path, monkeypatch, installed_fake, topology, child):
    from pet import file_interpret
    from pet.feed_presentation import OverlayInterpretTarget
    with hosted(tmp_path, topology, child) as h:
        set_target_config(h, 'self_talk_speak_enabled', True)
        set_target_config(h, 'proactive_bubble_speak_enabled', True)
        path = tmp_path/'unconfirmed.txt'
        path.write_text('PRIVATE SYNTHETIC CONTENT', encoding='utf-8')
        def forbidden(*_a, **_k):
            pytest.fail('read an unconfirmed file')
        monkeypatch.setattr(file_interpret, 'extract_text', forbidden)
        actor = OverlayInterpretTarget(h.host, h.target.sprite_ref()) if h.target.sprite_ref else None
        assert h.ctrl.offer([str(path)], target=actor)
        assert h.ctrl._service is None and spoken(h) == []
        h.ctrl._on_decline()
        assert h.ctrl._service is None and spoken(h) == []


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('kind', ['file', 'screen'])
def test_original_tts_failure_preserves_completed_reply(tmp_path, monkeypatch, topology, kind):
    from pet import vision
    from tests.test_voice_chime_service import _service, _WorkerSpy
    with hosted(tmp_path, topology) as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        set_target_config(h, 'self_talk_speak_enabled', True)
        set_target_config(h, 'proactive_bubble_speak_enabled', True)
        watcher = None
        try:
            if kind == 'file':
                file_request(h, tmp_path/'consented.txt')
                wait(h.app, lambda: h.ctrl._state == 'idle')
            else:
                h.cfg.set('proactive_screen', {'enabled': True})
                watcher = ProactiveScreenWatcher(MultiWindowProxy(h.shell), h.cfg)
                monkeypatch.setattr(vision, '_post_vision_request', lambda *a, **k: '合成识屏完成回复')
                watcher._worker_request_vision(b'synthetic', '', '', h.cfg.chat_settings().active_config, gen=watcher._generation)
            wait(h.app, lambda: len(_WorkerSpy.instances) == 1)
            text, receipt = h.bubble._raw_text, h.bubble.text_presentation_id
            _WorkerSpy.instances[0].finish(error='synthetic TTS unavailable')
            wait(h.app, lambda: not channel._busy)
            assert h.bubble._raw_text == text and h.bubble.text_presentation_id == receipt
            assert channel._player.plays == 0
        finally:
            if watcher:
                watcher.pause()


@pytest.mark.parametrize('kind', ['file', 'screen'])
def test_empty_ai_result_does_not_speak_completion_status(tmp_path, monkeypatch, kind):
    from pet import vision
    from pet.chat.service import ChatService
    from tests.test_companion_proactive_service import FakeProvider
    from pet.voice_chime_service import VoiceChimeService
    requests = []
    monkeypatch.setattr(VoiceChimeService, '_fire', lambda self, text, **kw: requests.append(text))
    with hosted(tmp_path, 'legacy') as h:
        set_target_config(h, 'self_talk_speak_enabled', True)
        set_target_config(h, 'proactive_bubble_speak_enabled', True)
        if kind == 'file':
            provider = FakeProvider([' '])
            provider.synthetic_acceptance = True
            h.ctrl._service_factory = lambda: ChatService(provider=provider)
            path = tmp_path/'consented.txt'
            path.write_text('SYNTHETIC CONTENT')
            h.ctrl.offer([str(path)])
            h.ctrl._on_confirm()
            wait(h.app, lambda: h.ctrl._state == 'idle')
        else:
            h.cfg.set('proactive_screen', {'enabled': True})
            watcher = ProactiveScreenWatcher(MultiWindowProxy(h.shell), h.cfg)
            monkeypatch.setattr(vision, '_post_vision_request', lambda *a, **k: '')
            watcher._worker_request_vision(b'synthetic', '', '', h.cfg.chat_settings().active_config, gen=watcher._generation)
            watcher.pause()
        assert requests == []
