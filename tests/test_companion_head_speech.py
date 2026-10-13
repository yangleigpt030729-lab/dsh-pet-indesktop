import pytest
from tests.test_companion_acceptance_launcher import installed_fake as _launcher_fake_fixture
from PySide6.QtWidgets import QApplication
from pet.config import Config
from pet.modern_settings_dialog import ModernSettingsDialog, SettingRow
from tests.test_companion_chat import wait


def test_single_head_row_moves_to_click_tab_and_shared_speech_visibility_persists(tmp_path):
    from pet.settings_widgets import SettingsTabContainer
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    dialog = ModernSettingsDialog(cfg, include_ai=True)
    try:
        rows = dialog.findChildren(SettingRow, 'settingRow_companion_head_touch_enabled')
        assert len(rows) == 1
        parent = next(dialog.pages.widget(i) for i in range(dialog.pages.count())
                      if dialog.sidebar.item(i).text() == '互动')
        assert parent.isAncestorOf(rows[0])
        tabs = parent.findChild(SettingsTabContainer)
        assert tabs.currentKey() == 'click'
        dialog.click_self_talk_check.setChecked(False)
        dialog.companion_head_touch_check.setChecked(True)
        row = dialog.findChild(SettingRow, 'settingRow_click_self_talk_speak')
        assert not row.isHidden()
        assert dialog.findChild(SettingRow, 'settingRow_click_talk_bindings').isHidden()
        assert dialog.select_page('摸头 AI') and tabs.currentKey() == 'click'
        assert Config(base=tmp_path).get('companion_interaction')['head_touch_enabled'] is True
        dialog.companion_head_touch_check.setChecked(False)
        assert row.isHidden()
        dialog.click_self_talk_check.setChecked(True)
        assert not row.isHidden()
        dialog._search_settings('摸头')
        assert any(r.objectName() == rows[0].objectName() for r in dialog._search_matches)
    finally:
        dialog.deleteLater()


def test_head_can_keep_original_audio_channel_without_ordinary_click(tmp_path):
    from pet.app import AppShell
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('click_show_self_talk', False)
    cfg.set('self_talk_speak_enabled', True)
    cfg.set('companion_interaction', {'head_touch_enabled': True})
    shell = AppShell(app, cfg)
    try:
        assert shell._self_talk_speak_wanted()
        shell._sync_chime_service()
        assert shell.voice_chime_service is not None
        cfg.set('companion_interaction', {'head_touch_enabled': False})
        shell._sync_chime_service()
        assert shell.voice_chime_service is None
        assert not cfg.get('click_show_self_talk')
    finally:
        if shell.voice_chime_service:
            shell.voice_chime_service.stop()
        shell._teardown_config_watcher()


def test_guarded_original_tts_drops_revoked_synthesis_and_queued_speech(tmp_path, monkeypatch):
    from tests.test_voice_chime_service import _service, _WorkerSpy
    service, host, cfg = _service(tmp_path, monkeypatch)
    service.apply_config()
    allowed = [True]
    assert service.speak('已展示摸头文字', valid=lambda: allowed[0], config=cfg)
    assert len(_WorkerSpy.instances) == 1
    assert service.speak('已展示第二句', valid=lambda: allowed[0], config=cfg)
    allowed[0] = False
    _WorkerSpy.instances[0].finish()
    wait(QApplication.instance(), lambda: not service._busy)
    service._terminal_statuses = ('END',)
    service._on_media_status('END')
    assert service._player.plays == 0 and len(_WorkerSpy.instances) == 1
    service.stop()


def set_target_config(h, key, value):
    if h.target.sprite_ref and h.target.sprite_ref() is not h.host.sprite:
        h.host.persist_sprite_setting(h.target.sprite_ref(), key, value)
    else:
        cfg = h.host._config if h.target.sprite_ref else h.target.config()
        cfg.set(key, value)
        cfg.save()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
@pytest.mark.parametrize('speak', [False, True])
def test_real_head_receipt_routes_exactly_once_through_original_shared_reader(tmp_path, monkeypatch, installed_fake, topology, child, speak):
    from tests.test_companion_feed_presentation import hosted
    from pet.companion.interaction_service import InteractionService
    from pet.chat.models import SecretStore
    import urllib.request
    def forbidden(*a, **k):
        pytest.fail('Fake head accessed a real network/key/audio synthesis')
    monkeypatch.setattr(SecretStore, 'get', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    from pet.voice_chime_service import _TTSWorker
    monkeypatch.setattr(_TTSWorker, 'run', forbidden)
    with hosted(tmp_path, topology, child) as h:
        h.cfg.set('self_talk_speak_enabled', False)
        set_target_config(h, 'self_talk_speak_enabled', speak)
        set_target_config(h, 'dialogue_mode', 'whale_maid')
        service = h.shell.companion_interactions = InteractionService()
        receipt = h.bubble.text_presentation_id
        assert service.request('head', h.target)
        wait(h.app, lambda: not service.busy)
        assert h.bubble.isVisible() and h.bubble.text_presentation_id > receipt
        assert '主人' in h.bubble._raw_text
        channel = h.shell.voice_chime_service
        if speak:
            assert h.shell._self_talk_speak_wanted()
            assert channel._acceptance_speech == [h.bubble._raw_text]
            assert h.shell.ensure_audio_channel() is channel  # Chime/festival/head share this one object.
        else:
            assert channel is None
        service.cooldowns.clear()
        assert service.request('feeding', h.target, {'categories': {'image': 1}, 'files': 1})
        wait(h.app, lambda: not service.busy)
        if speak:
            assert len(channel._acceptance_speech) == 1  # Feeding never opts into head speech.
        assert not list(h.cfg.dir.glob('*sessions*')) and not list(h.cfg.dir.glob('*memory*'))


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('revoke', ['speech', 'head', 'style', 'role', 'cancel', 'close', 'hide', 'expire'])
def test_real_displayed_head_pending_synthesis_is_revoked_without_replay(tmp_path, monkeypatch, topology, revoke):
    from tests.test_companion_feed_presentation import hosted
    from tests.test_companion_proactive_service import FakeProvider
    from tests.test_voice_chime_service import _service, _WorkerSpy
    from pet.companion.interaction_service import InteractionService
    with hosted(tmp_path, topology, child=True) as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        set_target_config(h, 'self_talk_speak_enabled', True)
        service = h.shell.companion_interactions = InteractionService(provider=FakeProvider(['已展示这句摸头回复。']))
        now = [10000.]
        service.clock = lambda: now[0]
        assert service.request('head', h.target)
        wait(h.app, lambda: not service.busy)
        assert len(_WorkerSpy.instances) == 1 and _WorkerSpy.instances[0].text == h.bubble._raw_text
        if revoke == 'speech':
            set_target_config(h, 'self_talk_speak_enabled', False)
        elif revoke == 'head':
            set_target_config(h, 'companion_interaction', {'head_touch_enabled': False})
        elif revoke == 'style':
            set_target_config(h, 'dialogue_mode', 'whale_maid')
        elif revoke == 'role':
            set_target_config(h, 'character', 'other-character')
        elif revoke == 'cancel':
            service.cancel()
        elif revoke == 'close':
            service.close()
        elif revoke == 'hide':
            h.host.hide() if topology == 'legacy' else h.host.overlay.hide()
        else:
            now[0] += 31
        _WorkerSpy.instances[0].finish()
        wait(h.app, lambda: not channel._busy)
        assert channel._player.plays == 0


def test_head_unshown_and_tts_error_keep_bubble_and_do_not_double_speak(tmp_path, monkeypatch):
    from tests.test_companion_feed_presentation import hosted
    from tests.test_companion_proactive_service import FakeProvider
    from tests.test_voice_chime_service import _service, _WorkerSpy
    from pet.companion.interaction_service import InteractionService
    with hosted(tmp_path, 'legacy') as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        set_target_config(h, 'self_talk_speak_enabled', True)
        provider = FakeProvider(['先显示这句。', '第二句无法显示。'])
        service = h.shell.companion_interactions = InteractionService(provider=provider)
        assert service.request('head', h.target)
        wait(h.app, lambda: not service.busy)
        text = h.bubble._raw_text
        _WorkerSpy.instances[0].finish(error='simulated offline')
        wait(h.app, lambda: not channel._busy)
        assert h.bubble._raw_text == text and channel._player.plays == 0
        service.cooldowns.clear()
        monkeypatch.setattr(h.host, 'show_bubble', lambda *a, **k: None)
        assert service.request('head', h.target)
        wait(h.app, lambda: not service.busy)
        assert len(_WorkerSpy.instances) == 1


def test_child_original_voice_receives_own_voice_rate_pitch_volume_and_reuses_cache(tmp_path, monkeypatch):
    from tests.test_companion_feed_presentation import hosted
    from tests.test_companion_proactive_service import FakeProvider
    from tests.test_voice_chime_service import _service, _WorkerSpy
    from pet.companion.interaction_service import InteractionService
    from pet.voice_chime_service import VoiceChimeService
    observed = []
    class Worker(_WorkerSpy):
        def __init__(self, text, voice, rate, pitch, out_path, on_done):
            observed.append((text, voice, rate, pitch))
            super().__init__(text, voice, rate, pitch, out_path, on_done)
    with hosted(tmp_path, 'overlay', child=True) as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        monkeypatch.setattr('pet.voice_chime_service._TTSWorker', Worker)
        for key, value in {'self_talk_speak_enabled': True, 'voice_chime_voice': 'zh-CN-XiaoyiNeural',
                           'voice_chime_rate': 15, 'voice_chime_pitch': 5, 'voice_chime_volume': 23}.items():
            set_target_config(h, key, value)
        service = h.shell.companion_interactions = InteractionService(provider=FakeProvider(['独立子宠的一句。']))
        assert service.request('head', h.target)
        wait(h.app, lambda: not service.busy)
        assert observed == [(h.bubble._raw_text, 'zh-CN-XiaoyiNeural', '+15%', '+5Hz')]
        worker = _WorkerSpy.instances[0]
        worker.out_path.write_bytes(b'synthetic audio cache')
        worker.finish()
        wait(h.app, lambda: not channel._busy)
        assert channel._player.plays == 1 and channel._audio_out.volumes[-1] == .23
        # Dynamic cache uses the original voice/rate/pitch key and single player.
        assert VoiceChimeService.speak(channel, h.bubble._raw_text, valid=lambda: True, config=h.target.config())
        assert len(observed) == 1 and channel._player.plays == 2


def test_runtime_memory_and_speech_revocation_cannot_resurrect_pending_private_audio(tmp_path, monkeypatch):
    from tests.test_companion_feed_presentation import hosted
    from tests.test_companion_proactive_service import FakeProvider
    from tests.test_voice_chime_service import _service, _WorkerSpy
    from pet.companion.interaction_service import InteractionService
    from pet.companion.memory_context import MemoryContext
    from pet.companion.proactive_policy import set_enabled
    with hosted(tmp_path, 'overlay', child=True) as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        channel.apply_config()
        h.shell.voice_chime_service = channel
        set_target_config(h, 'self_talk_speak_enabled', True)
        service = h.shell.companion_interactions = InteractionService(provider=FakeProvider(['已显示的一句。']))
        assert service.request('head', h.target)
        wait(h.app, lambda: not service.busy)
        assert len(_WorkerSpy.instances) == 1
        path = h.target.config().path
        # Failed save / rapid off-on: generations revoke this already-created ticket.
        MemoryContext.set_runtime_policy(path, False)
        MemoryContext.set_runtime_policy(path, True)
        set_enabled(path, False, feature='self_talk_speak_enabled')
        set_enabled(path, True, feature='self_talk_speak_enabled')
        _WorkerSpy.instances[0].finish()
        wait(h.app, lambda: not channel._busy)
        assert channel._player.plays == 0


@pytest.fixture
def installed_fake(monkeypatch):
    return _launcher_fake_fixture.__wrapped__(monkeypatch)


def test_no_chat_capability_has_no_head_control_or_extra_voice_channel(tmp_path):
    from types import SimpleNamespace
    from pet.companion.head_speech import wanted
    QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('companion_interaction', {'head_touch_enabled': True})
    cfg.set('self_talk_speak_enabled', True)
    cfg.set('click_show_self_talk', False)
    dialog = ModernSettingsDialog(cfg, include_ai=False)
    try:
        assert not dialog.findChildren(SettingRow, 'settingRow_companion_head_touch_enabled')
        assert dialog.findChild(SettingRow, 'settingRow_click_self_talk_speak').isHidden()
        assert not wanted(SimpleNamespace(config=cfg, enable_chat=False))
    finally:
        dialog.deleteLater()
