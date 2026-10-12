from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QPushButton
from pet.config import Config
from pet.chat.ai_settings_page import _AiSettingsPage
from pet.companion.memory_store import MemoryStore
from pet.companion.memory_dialog import MemoryDialog
from tests.test_companion_chat import wait


def test_policy_controls_immediate_persist_defaults_and_management(tmp_path):
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    page = _AiSettingsPage(cfg)
    assert not page.memory_enabled.isChecked()
    assert not page.memory_auto_extract.isEnabled()
    page.memory_enabled.setChecked(True)
    page.memory_auto_extract.setChecked(True)
    reopened = Config(base=tmp_path).chat_settings()
    assert reopened.memory_enabled and reopened.memory_auto_extract
    page.memory_enabled.setChecked(False)
    assert not Config(base=tmp_path).chat_settings().memory_enabled
    page.save()
    cfg.save()
    assert not Config(base=tmp_path).chat_settings().memory_enabled
    assert isinstance(page.memory_manage, QPushButton)
    assert app.thread() == QThread.currentThread()


def test_manager_crud_real_sqlite_and_background_thread(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    threads = []
    original = MemoryStore.list
    def record(store):
        threads.append(QThread.currentThread())
        return original(store)
    monkeypatch.setattr(MemoryStore, 'list', record)
    dialog = MemoryDialog(tmp_path)
    wait(app, lambda: not dialog._busy)
    dialog.editor.setPlainText('我喜欢蓝色')
    dialog.add_button.click()
    wait(app, lambda: not dialog._busy)
    assert dialog.items.count() == 1
    dialog.items.setCurrentRow(0)
    dialog.editor.setPlainText('我喜欢绿色')
    dialog.save_button.click()
    wait(app, lambda: not dialog._busy)
    assert dialog.items.item(0).text() == '我喜欢绿色'
    dialog.items.setCurrentRow(0)
    dialog.delete_button.click()
    wait(app, lambda: not dialog._busy)
    assert dialog.items.count() == 0
    assert threads and all(t != app.thread() for t in threads)
    dialog.reject()


def test_manager_corruption_shows_error_not_crash(tmp_path):
    app = QApplication.instance() or QApplication([])
    (tmp_path / 'companion_memory.sqlite3').write_bytes(b'broken')
    dialog = MemoryDialog(tmp_path)
    wait(app, lambda: not dialog._busy)
    assert '暂不可用' in dialog.status.text()
    assert dialog.items.count() == 0
    dialog.reject()


def test_memory_rows_visible_in_existing_ai_domain(tmp_path):
    app = QApplication.instance() or QApplication([])
    from pet.modern_settings_dialog import ModernSettingsDialog
    dialog = ModernSettingsDialog(Config(base=tmp_path), include_ai=True)
    dialog.show()
    app.processEvents()
    ai = dialog.ai_page
    assert ai is not None
    index = next(i for i in range(dialog.sidebar.count()) if dialog.sidebar.item(i).text() == 'AI 与对话')
    assert dialog.pages.widget(index).isAncestorOf(ai.memory_manage)
    from pet.settings_widgets import SettingRow
    for key in ('memory_enabled', 'memory_auto_extract', 'memory_manage'):
        assert dialog.findChild(SettingRow, 'settingRow_' + key) is not None
    dialog.close()
