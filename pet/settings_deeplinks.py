"""Settings aliases and modeless preview fallback, outside the large dialog."""
from PySide6.QtWidgets import QScrollArea
from .settings_widgets import SettingRow


def select_target(dialog, target):
    if target in ('摸头 AI', '点击与音效'):
        from .settings_widgets import SettingsTabContainer
        dialog.select_page('互动')
        tabs = dialog.pages.currentWidget().findChild(SettingsTabContainer)
        if tabs is not None:
            tabs.setCurrentKey('click')
        return True
    if target != '主动识屏':
        return False
    dialog.select_page('自动化与联动')
    page = dialog.pages.currentWidget()
    row = dialog.findChild(SettingRow, 'settingRow_proactive_enabled')
    scroll = page if isinstance(page, QScrollArea) else page.findChild(QScrollArea)
    if scroll is not None and row is not None:
        scroll.ensureWidgetVisible(row, 0, 24)
    return True


def preview_voice(dialog, text):
    if dialog.standalone:
        from .settings_standalone import preview_voice_chime
        preview_voice_chime(dialog, text)
        return
    callback = getattr(dialog.parent(), 'on_voice_chime_now', None)
    if not callable(callback):
        callback = getattr(getattr(dialog, '_preview_host', None), 'trigger_voice_chime_now', None)
    if callable(callback):
        callback(text)
