"""In-process rename notification; headers only, never reload a chat session."""
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

class _Names(QObject):
    changed = Signal(str, str, str)

_bus = None

def bus():
    global _bus
    if _bus is None and QApplication.instance() is not None:
        _bus = _Names(QApplication.instance())
    return _bus

def notify(config, character_id, name):
    current = bus()
    if current is not None:
        current.changed.emit(str(config.path), character_id, name)

def watch(window):
    if getattr(window, '_name_subscription', False):
        return
    current = bus()
    if current is None:
        return
    window._name_subscription = True
    # Bound receiver: Qt disconnects automatically when the window is destroyed.
    current.changed.connect(window._character_name_changed)

def changed(window, path, character_id, name):
    if str(window.config.path) != path:
        return
    aliases = window.config.data.setdefault('character_aliases', {})
    if name:
        aliases[character_id] = name
    else:
        aliases.pop(character_id, None)
    if window.character_id == character_id:
        window._apply_character_theme()
