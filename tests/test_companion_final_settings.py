from PySide6.QtWidgets import QApplication
from pet.config import Config
from pet.modern_settings_dialog import ModernSettingsDialog, SettingRow
from pet.companion.memory_store import MemoryStore
from pet.companion.proactive_state import ProactiveState
from tests.test_companion_proactive_state import START, CFG
from tests.test_companion_interactions import setup
from tests.test_companion_proactive_service import FakeProvider


def test_interaction_settings_live_save_and_failed_opt_out(tmp_path, monkeypatch):
    from pet.companion.interaction_settings import InteractionSettings
    app, cfg, target, s = setup(tmp_path, FakeProvider(['本鱼很开心。']))
    other = Config(base=tmp_path)
    page = InteractionSettings(other)
    try:
        assert page.controls['head_touch_enabled'].isChecked()
        monkeypatch.setattr(other, 'save', lambda: False)
        page.controls['head_touch_enabled'].setChecked(False)
        assert not s.request('head', target)
        assert not s.busy
    finally:
        s.close()
        page.deleteLater()


def test_clear_screen_activity_preserves_both_private_sqlite_databases(tmp_path):
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    store = MemoryStore(cfg.dir/'companion_memory.sqlite3')
    store.put('color', '我喜欢蓝色', 'preference')
    state = ProactiveState(cfg.dir/'companion_proactive.sqlite3')
    token = state.reserve('synthetic', 'care', START, CFG, 'fake')
    state.mark_presenting(token, START)
    state.finish(token, '合成测试', [], START, True)
    dialog = ModernSettingsDialog(cfg)
    if not hasattr(dialog, 'pro_clear_mem_btn'):
        dialog._build_proactive_controls()  # Windows-only controls, real Qt on Linux.
    try:
        assert dialog.pro_clear_mem_btn.text() == '清除记录'
        dialog._on_pro_clear_memory()
        assert store.list()[0].content == '我喜欢蓝色'
        assert state.stats(START.date().isoformat())['successes'] == 1
    finally:
        dialog.deleteLater()


def test_proactive_screen_deeplink_selects_automation_domain(tmp_path):
    app = QApplication.instance() or QApplication([])
    dialog = ModernSettingsDialog(Config(base=tmp_path), initial_page='主动识屏')
    try:
        assert dialog.sidebar.currentItem().text() == '自动化与联动'
    finally:
        dialog.deleteLater()


def test_official_parentless_inprocess_settings_voice_preview_is_wired(tmp_path, monkeypatch):
    from pet.app import PetInstance
    from tests.test_settings_process_isolation import _bare_shell
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('settings_process_isolation', False)
    shell = _bare_shell(cfg)
    shell.enable_chat = True
    calls = []
    shell.trigger_voice_chime_now = calls.append
    shell.trigger_festival_now = lambda: calls.append('festival')
    owner = PetInstance(shell, cfg)
    shell._instances = [owner]
    owner.open_modern_settings()
    dialog = owner.modern_settings_dialog
    try:
        dialog.voice_chime_page.preview_requested.emit('合成试听')
        assert calls == ['合成试听']
    finally:
        dialog.deleteLater()


def test_interaction_rows_belong_to_existing_ai_domain(tmp_path):
    app = QApplication.instance() or QApplication([])
    dialog = ModernSettingsDialog(Config(base=tmp_path), include_ai=True)
    try:
        for setting in ('companion_head_touch_enabled', 'companion_feeding_enabled'):
            row = dialog.findChild(SettingRow, 'settingRow_'+setting)
            assert row is not None
            parent = row.parentWidget()
            while parent is not None and parent.objectName() != 'settingsDomain_ai':
                parent = parent.parentWidget()
            assert parent is not None
    finally:
        dialog.deleteLater()
