from types import SimpleNamespace
import pytest
from PySide6.QtWidgets import QApplication, QScrollArea
from pet.config import Config
from pet.chat.ai_settings_page import _AiSettingsPage
from pet.modern_settings_dialog import ModernSettingsDialog
from pet.settings_widgets import SettingRow, ToggleSwitch
from pet.companion import proactive_runtime as runtime
from tests.test_overlay_chat_proactive import _make_shell
from tests.test_companion_chat import wait


@pytest.mark.parametrize('width', [720, 1100])
def test_settings_in_existing_ai_domain_roundtrip(tmp_path, width):
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    dialog = ModernSettingsDialog(cfg, include_ai=True)
    dialog.resize(width, 800)
    dialog.show()
    index = next(i for i in range(dialog.sidebar.count()) if dialog.sidebar.item(i).text() == 'AI 与对话')
    dialog.sidebar.setCurrentRow(index)
    app.processEvents()
    page = dialog.ai_page.proactive_settings
    assert not page.controls['enabled'].isChecked()
    assert not page.controls['daily_limit'].isEnabled()
    page.controls['enabled'].setChecked(True)
    page.controls['daily_limit'].setValue(7)
    values = Config(base=tmp_path).get('proactive_chat')
    assert values['enabled'] and values['daily_limit'] == 7
    scheduled = dialog.findChild(SettingRow, 'settingRow_proactive_chat_scheduled_reminders')
    assert scheduled is not None
    assert not scheduled.findChildren(ToggleSwitch)[0].isEnabled()
    scroll = dialog.pages.currentWidget().findChild(QScrollArea, 'settingsScroll')
    assert scroll is not None and scroll.verticalScrollBar().maximum() > 0
    page.controls['enabled'].setChecked(False)
    assert not Config(base=tmp_path).get('proactive_chat')['enabled']
    dialog.reject()


def test_immediate_setting_merges_and_preserves_todo(tmp_path):
    cfg = Config(base=tmp_path)
    page = _AiSettingsPage(cfg)
    external = Config(base=tmp_path)
    external.set('todo_reminder_enabled', False)
    external.set('proactive_chat', {'enabled': True, 'daily_limit': 6})
    external.save()
    page.proactive_settings.controls['use_memory'].setChecked(False)
    reopened = Config(base=tmp_path)
    assert reopened.get('proactive_chat')['daily_limit'] == 6
    assert not reopened.get('todo_reminder_enabled')
    assert not reopened.get('proactive_chat')['use_memory']
    page.deleteLater()


def test_overlay_real_follower_receipt_and_gates(tmp_path):
    app = QApplication.instance() or QApplication([])
    shell, _ = _make_shell(tmp_path)
    try:
        shell.overlay.show()
        assert shell.try_show_bubble('本鱼来陪你看看云。') is True
        assert shell._speech_bubble.isVisible()
        shell._bubble_busy_until = 0
        shell._bubble_suppressed = True
        assert not shell.try_show_bubble('不应出现')
        shell._bubble_suppressed = False
        shell.driver.set_suspended(True)
        assert not shell.try_show_bubble('不应出现')
        shell.driver.set_suspended(False)
        shell._sticky_bubble_active = True
        assert not shell.try_show_bubble('不应覆盖审批')
        shell._sticky_bubble_active = False
        shell.set_pet_visible(False)
        assert not shell.try_show_bubble('隐藏不显示')
    finally:
        shell.stop()
        shell.overlay.close()
        shell._delete_runtime_marker()
        app.processEvents()


def test_legacy_real_window_receipt(tmp_path):
    from pet.window import PetWindow
    from tests.test_window_broker_wiring import FakeLibrary
    app = QApplication.instance() or QApplication([])
    win = PetWindow(FakeLibrary(), Config(base=tmp_path))
    try:
        win.show()
        app.processEvents()
        assert win.try_show_bubble('本鱼陪你休息一下。')
        assert win._speech_bubble.isVisible()
        win._bubble_busy_until = 0
        win._sticky_bubble_active = True
        assert not win.try_show_bubble('不覆盖重要提示')
        win._sticky_bubble_active = False
        win.hide()
        assert not win.try_show_bubble('隐藏不显示')
    finally:
        win.close()
        app.processEvents()


def test_single_host_not_broadcast_and_destroyed_host(tmp_path):
    calls = []
    class Host:
        def can_show_proactive_bubble(self):
            return True
        def try_show_bubble(self, text):
            calls.append(text)
            return True
    first, second = Host(), Host()
    shell = SimpleNamespace(instances=[SimpleNamespace(win=first), SimpleNamespace(win=second)])
    assert runtime.present(shell, '仅一个气泡')
    assert calls == ['仅一个气泡']
    first.can_show_proactive_bubble = lambda: (_ for _ in ()).throw(RuntimeError('deleted Qt object'))
    assert runtime.host(shell) is second


def test_no_chat_never_imports_or_creates_service(tmp_path):
    cfg = Config(base=tmp_path)
    cfg.set('proactive_chat', {'enabled': True})
    shell = SimpleNamespace(enable_chat=False, config=cfg)
    runtime.sync(shell)
    assert getattr(shell, 'companion_service', None) is None


def test_runtime_suspend_resets_and_lazy_disable(tmp_path, monkeypatch):
    from pet.companion.proactive_schedule import Snapshot
    from tests.test_companion_proactive_service import FakeProvider
    from pet.companion.proactive_service import ProactiveService
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('proactive_chat', {'enabled': True})
    cfg.save()
    shell = SimpleNamespace(enable_chat=True, config=cfg)
    monkeypatch.setattr(runtime, 'snapshot', lambda _: Snapshot(suspended=getattr(shell, '_companion_suspended', False)))
    monkeypatch.setattr(runtime, 'present', lambda *_: True)
    import pet.companion.proactive_service as module
    monkeypatch.setattr(module, 'ProactiveService', lambda *a, **k: ProactiveService(*a, **k, provider=FakeProvider()))
    runtime.sync(shell)
    s = shell.companion_service
    assert s.timer.isActive()
    s.scheduler.activity = 7200
    runtime.suspend(shell, True, 'lock')
    assert s.scheduler.activity == 0
    s.tick()
    assert not s.busy and not s.chat.provider.calls
    runtime.suspend(shell, False, 'unlock')
    cfg.set('proactive_chat', {'enabled': False})
    runtime.sync(shell)
    assert not s.timer.isActive()
    runtime.close(shell)
    wait(app, lambda: not s.busy)


def test_failed_opt_out_save_cancels_another_config_snapshot(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from pet.companion.proactive_service import ProactiveService
    from pet.companion.proactive_schedule import Snapshot
    from tests.test_companion_proactive_service import FakeProvider
    app = QApplication.instance() or QApplication([])
    original = Config(base=tmp_path)
    original.set('proactive_chat', {'enabled': True})
    original.save()
    page_config = Config(base=tmp_path)
    page = _AiSettingsPage(page_config)
    s = ProactiveService(original, lambda: Snapshot(), lambda _: True, provider=FakeProvider())
    monkeypatch.setattr(page_config, 'save', lambda: False)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: None)
    page.proactive_settings.controls['enabled'].setChecked(False)
    assert original.get('proactive_chat')['enabled'] is True  # stale separate snapshot
    s.tick()
    assert not s.timer.isActive() and not s.busy and not s.chat.provider.calls
    s.close()
    page.deleteLater()
    app.processEvents()


def test_app_shell_session_callback_is_wired_for_chat_variant(tmp_path, monkeypatch):
    from pet import app as app_module
    from pet.app import AppShell
    from pet.session_watcher import SessionWatcher
    app = QApplication.instance() or QApplication([])
    callbacks = []
    def install(*, app=None, on_session_end=None, on_suspend_change=None):
        callbacks.append(on_suspend_change)
        return SessionWatcher(app=app, on_session_end=on_session_end, on_suspend_change=on_suspend_change, install_native_filter=False)
    monkeypatch.setattr(app_module, 'install_session_watcher', install)
    shell = AppShell(app, Config(base=tmp_path), enable_chat=True)
    try:
        shell._install_session_watcher()
        callbacks[0](True, 'lock')
        assert shell._companion_suspended is True
        callbacks[0](False, 'unlock')
        assert shell._companion_suspended is False
    finally:
        AppShell._shutdown_live_for_tests()


def test_normal_quit_closes_companion_without_session_watcher_fallback(tmp_path, monkeypatch):
    from pet.app import AppShell
    from pet.chat import session_store
    app = QApplication.instance() or QApplication([])
    shell = AppShell(app, Config(base=tmp_path), enable_chat=False)
    closed = []
    shell.companion_service = SimpleNamespace(close=lambda: closed.append(True))
    monkeypatch.setattr(shell, '_mark_session_ending', lambda: None)
    monkeypatch.setattr(shell, '_stop_self_launched_harness', lambda: None)
    monkeypatch.setattr(session_store, 'close_all_writers', lambda **kwargs: True)
    try:
        shell._on_about_to_quit()
        assert closed == [True]
    finally:
        AppShell._shutdown_live_for_tests()


def test_overlay_hidden_primary_and_flight_do_not_display(tmp_path):
    app = QApplication.instance() or QApplication([])
    shell, _ = _make_shell(tmp_path)
    try:
        shell.overlay.show()
        shell.set_sprite_visible(shell.sprite, False)
        assert not shell.try_show_bubble('隐藏宠物不应冒泡')
        shell.set_sprite_visible(shell.sprite, True)
        shell._flying_sprites.add(shell.sprite)
        assert not shell.try_show_bubble('飞行不应冒泡')
    finally:
        shell.stop()
        shell.overlay.close()
        shell._delete_runtime_marker()
        app.processEvents()
