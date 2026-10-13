"""Actual Qt menus/settings/receipts with synthetic worker and playback boundaries."""
import json
import threading
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMenu, QSlider, QPushButton, QApplication
from pet.config import Config
from pet.voice_volume import values, write, semantic_stamp
from pet.context_menus.voice_volume import build_volume_menu
from tests.test_companion_chat import wait
from tests.test_companion_feed_presentation import hosted
from tests.test_companion_head_speech import set_target_config


@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_actual_menu_slider_mute_stays_open_and_retains_volume(tmp_path, theme):
    from pet.context_menus.menu_styles.modern import apply_modern_menu_style
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('voice_chime_volume', 67)
    cfg.save()
    menu = QMenu()
    apply_modern_menu_style(menu, {'theme': theme})
    sub = build_volume_menu(menu, SimpleNamespace(cfg=cfg))
    slider = sub.findChild(QSlider, 'speechVolumeSlider')
    mute = sub.findChild(QPushButton, 'speechVolumeMute')
    try:
        menu.popup(QPoint(30, 30))
        menu.setActiveAction(sub.menuAction())
        sub.popup(QPoint(250, 30))
        app.processEvents()
        assert slider.value() == 67
        QTest.mouseClick(mute, Qt.LeftButton)
        assert values(cfg) == (67, True)
        assert sub.isVisible() and menu.isVisible()
        QTest.mouseClick(mute, Qt.LeftButton)
        assert values(Config(base=tmp_path)) == (67, False)
        QTest.mouseClick(mute, Qt.LeftButton)
        slider.setFocus()
        QTest.keyClick(slider, Qt.Key_Left)
        assert values(cfg) == (66, False)
        assert sub.isVisible()
    finally:
        sub.close()
        menu.close()
        menu.deleteLater()
        app.processEvents()


def test_settings_and_menu_sync_and_late_save_cannot_overwrite(tmp_path):
    from pet.modern_settings_dialog import ModernSettingsDialog
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.save()
    dialog = ModernSettingsDialog(Config(base=tmp_path), include_ai=True)
    menu = QMenu()
    sub = build_volume_menu(menu, SimpleNamespace(cfg=cfg))
    slider = sub.findChild(QSlider, 'speechVolumeSlider')
    try:
        slider.setValue(29)
        assert dialog.voice_chime_page.volume_spin.value() == 29
        dialog.voice_chime_page.volume_spin.setValue(51)
        assert slider.value() == 51 and values(cfg) == (51, False)
        # Another process writes without the in-process bus; save before watcher dispatch.
        external = Config(base=tmp_path)
        external.set('voice_chime_volume', 38)
        external.save()
        assert dialog._write_config()
        assert values(Config(base=tmp_path)) == (38, False)
        assert dialog.voice_chime_page.volume_spin.value() == 38
        app.processEvents()
        wait(app, lambda: slider.value() == 38)
    finally:
        dialog._saved_via_button = True
        dialog.close()
        dialog.deleteLater()
        menu.deleteLater()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
def test_hot_volume_does_not_revoke_waiting_or_playing_reply(tmp_path, monkeypatch, topology, child):
    from tests.test_voice_chime_service import _service, _WorkerSpy
    from pet.companion.head_speech import speak_target
    from pet.context_menus.voice_volume import build_volume_menu
    from pet.sprite_menu_facade import SpriteMenuFacade
    with hosted(tmp_path, topology, child) as h:
        channel, _, _ = _service(tmp_path/'voice', monkeypatch)
        h.shell.voice_chime_service = channel
        set_target_config(h, 'self_talk_speak_enabled', True)
        assert h.target.present('合成音量测试回复')
        identity = h.target.identity()
        speak_target(h.target, h.bubble._raw_text, lambda: True)
        wait(h.app, lambda: len(_WorkerSpy.instances) == 1)
        pet = SpriteMenuFacade(h.host, h.target.sprite_ref()) if topology == 'overlay' else h.host
        menu = QMenu()
        sub = build_volume_menu(menu, pet)
        slider = sub.findChild(QSlider, 'speechVolumeSlider')
        mute = sub.findChild(QPushButton, 'speechVolumeMute')
        try:
            slider.setValue(31)
            assert h.target.identity() == identity
            worker = _WorkerSpy.instances[0]
            worker.out_path.write_bytes(b'synthetic MP3')
            worker.finish()
            wait(h.app, lambda: not channel._busy)
            assert channel._player.plays == 1 and channel._audio_out.volumes[-1] == .31
            mute.click()
            assert channel._audio_out.volumes[-1] == 0 and channel._player.plays == 1
            mute.click()
            assert channel._audio_out.volumes[-1] == .31
            slider.setValue(72)
            assert channel._audio_out.volumes[-1] == .72
            if child:
                assert Config(base=h.cfg.dir.parent).get('voice_chime_volume') == 80
                assert Config(base=h.cfg.dir.parent).get('voice_chime_muted') is False
        finally:
            menu.deleteLater()


def test_volume_sparse_slot_patch_and_semantic_revocation(tmp_path):
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path, instance_id='slot-1')
    cfg.dir.mkdir(parents=True, exist_ok=True)
    cfg.path.write_text(json.dumps({'character':'shenshen', 'voice_chime_volume':43, 'extension_preference':'preserve'}))
    initial = semantic_stamp(cfg)
    assert write(cfg, muted=True)
    assert semantic_stamp(cfg) == initial
    raw = json.loads(cfg.path.read_text())
    assert raw == {'character':'shenshen', 'voice_chime_volume':43, 'extension_preference':'preserve', 'voice_chime_muted':True, 'user_customized':True}
    assert write(cfg, volume=35)
    assert semantic_stamp(cfg) == initial
    raw['character'] = 'different-role'
    cfg.path.write_text(json.dumps(raw))
    changed = semantic_stamp(cfg)
    assert changed != initial
    cfg.path.write_text('[]')  # Valid JSON, invalid config object: revoke safely.
    assert semantic_stamp(cfg) != changed
    assert not write(cfg, volume=25)
    assert cfg.path.read_text() == '[]'
    assert app is not None


def test_failed_volume_save_keeps_prior_value(tmp_path, monkeypatch):
    from pet import slot_manager
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.save()
    before = cfg.path.read_bytes()
    def denied(*a):
        raise PermissionError('synthetic filesystem failure')
    monkeypatch.setattr(slot_manager, '_atomic_write_text', denied)
    assert not write(cfg, volume=5)
    assert cfg.path.read_bytes() == before and values(cfg) == (80, False)
    assert app is not None


def test_external_process_updates_open_settings_without_polling(tmp_path):
    import subprocess
    import sys
    from pet.voice_chime_settings import VoiceChimeSettingsPage
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.save()
    page = VoiceChimeSettingsPage(cfg)
    try:
        script = "from pet.config import Config; from pathlib import Path; import sys; c=Config(base=Path(sys.argv[1])); c.set('voice_chime_volume',46); c.set('voice_chime_muted',True); assert c.save()"
        result = subprocess.run([sys.executable, '-c', script, str(tmp_path)], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        wait(app, lambda: page.volume_spin.value() == 46)
        assert '静音' in page.volume_spin.toolTip()
        page.volume_spin.setValue(54)
        assert values(Config(base=tmp_path)) == (54, False)
    finally:
        page.deleteLater()
        app.processEvents()


def test_volume_update_applies_to_queued_and_cached_audio(tmp_path, monkeypatch):
    from tests.test_voice_chime_service import _service, _WorkerSpy
    service, app, cfg = _service(tmp_path, monkeypatch)
    service.apply_config()
    try:
        assert service.speak('合成第一句', valid=lambda: True, config=cfg)
        assert service.speak('合成第二句', valid=lambda: True, config=cfg)
        assert write(cfg, volume=24)
        worker = _WorkerSpy.instances[0]
        worker.out_path.write_bytes(b'synthetic MP3')
        worker.finish()
        wait(QApplication.instance(), lambda: not service._busy)
        assert service._audio_out.volumes[-1] == .24
        service._terminal_statuses = ('DONE',)
        assert write(cfg, volume=61)
        service._on_media_status('DONE')
        assert len(_WorkerSpy.instances) == 2
        second = _WorkerSpy.instances[1]
        second.out_path.write_bytes(b'synthetic MP3')
        second.finish()
        wait(QApplication.instance(), lambda: not service._busy)
        assert service._audio_out.volumes[-1] == .61
        assert write(cfg, muted=True)
        # The second recording must finish before its cached replay, rather
        # than relying on a player double that reports idle while still loaded.
        service._on_media_status('DONE')
        assert service.speak('合成第二句', valid=lambda: True, config=cfg)
        assert len(_WorkerSpy.instances) == 2  # same cached MP3, zero new synthesis
        assert service._audio_out.volumes[-1] == 0
        assert {'queue', 'cache_hit', 'synthesis_total', 'play_request'} <= {k for k,v in service.timings}
    finally:
        service.stop()


def test_default_false_mute_roundtrip_and_invalid_volume(tmp_path):
    QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    assert values(cfg) == (80, False)
    cfg.save()
    assert write(cfg, volume=130)
    assert values(Config(base=tmp_path)) == (100, False)
    assert write(cfg, muted=True)
    assert values(Config(base=tmp_path)) == (100, True)
    assert write(cfg, volume=-10)
    assert values(Config(base=tmp_path)) == (0, False)


def test_volume_does_not_cancel_ordinary_proactive_or_reset_quota(tmp_path):
    from tests.test_companion_proactive_service import FakeProvider, setup
    QApplication.instance() or QApplication([])
    app, cfg, service, bubbles = setup(tmp_path, FakeProvider())
    try:
        generation, identity = service.generation, service.identity
        before = service.state.stats('2026-10-13')
        assert write(cfg, volume=22)
        service.apply_config()
        assert service.generation == generation and service.identity == identity
        assert service.state.stats('2026-10-13') == before
    finally:
        service.close()


def test_custom_old_menu_layout_gets_volume_and_explicit_hide_survives(tmp_path):
    from pet.menu_layout import resolve_menu_layout
    from pet.context_menus.registry import MENU_ACTIONS
    old = {'schema_version':1, 'layout_id':'user', 'nodes':[
        {'type':'action','id':'size','visible':True}, {'type':'action','id':'modern_settings','visible':True},
        {'type':'action','id':'quit','visible':True}]}
    result = resolve_menu_layout(old, registered_actions=MENU_ACTIONS.ids, available_actions=MENU_ACTIONS.ids)
    names = [node['id'] for node in result.nodes]
    assert names.index('voice_volume') > names.index('size')
    old['nodes'].insert(1, {'type':'action','id':'voice_volume','visible':False})
    result = resolve_menu_layout(old, registered_actions=MENU_ACTIONS.ids, available_actions=MENU_ACTIONS.ids)
    assert 'voice_volume' not in [node['id'] for node in result.nodes]


def test_replaced_actor_volume_binding_cannot_change_current_audio(tmp_path, monkeypatch):
    from tests.test_voice_chime_service import _service
    service, _, cfg = _service(tmp_path, monkeypatch)
    cfg.save()
    child = Config(base=tmp_path, instance_id='slot-1')
    child.set('voice_chime_volume', 27)
    child.save()
    try:
        service._set_playback_volume(cfg)
        previous = service._volume_binding
        service._set_playback_volume(child)
        assert service._audio_out.volumes[-1] == .27
        assert write(cfg, volume=11)
        # Even before DeferredDelete runs, the old actor has no audio consumer.
        previous.refresh()
        assert service._audio_out.volumes[-1] == .27
        assert write(child, volume=39)
        assert service._audio_out.volumes[-1] == .39
    finally:
        service.stop()
