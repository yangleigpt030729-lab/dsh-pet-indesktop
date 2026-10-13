"""One persisted speech volume; mute retains it. GUI bindings are event driven."""
from collections import OrderedDict
import hashlib
import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QFileSystemWatcher
from .voice_chime import clean_volume, DEFAULT_VOLUME

VOLUME = 'voice_chime_volume'
MUTED = 'voice_chime_muted'
_semantic = OrderedDict()
_bus_instance = None


class _Bus(QObject):
    changed = Signal(str)


def _bus():
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = _Bus()
    return _bus_instance


def values(config):
    raw = config
    path = getattr(config, 'path', None)
    if path is not None:
        try:
            saved = json.loads(Path(path).read_text(encoding='utf-8'))
            if isinstance(saved, dict):
                raw = saved
        except (OSError, ValueError):
            pass
    return (clean_volume(raw.get(VOLUME, raw.get('volume', DEFAULT_VOLUME))), raw.get(MUTED) is True)


def effective(config):
    volume, muted = values(config)
    return 0 if muted else volume


def write(config, *, volume=None, muted=None):
    """Merge just these keys with the latest file; never replace stored volume on mute."""
    if getattr(config, 'path', None) is None:
        if volume is not None:
            config.set(VOLUME, clean_volume(volume))
            config.set(MUTED, False)
        if muted is not None:
            config.set(MUTED, muted is True)
        return True  # existing non-persistent settings/preview adapters
    from .slot_manager import _atomic_write_text
    try:
        try:
            raw = json.loads(config.path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            raw = config._redacted_data()
        if not isinstance(raw, dict):
            return False
        if volume is not None:
            raw[VOLUME] = clean_volume(volume)
            raw[MUTED] = False
        if muted is not None:
            raw[MUTED] = muted is True
        if config.instance_id:
            raw['user_customized'] = True
        config.dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(config.path, json.dumps(raw, ensure_ascii=False, indent=2))
    except (OSError, ValueError):
        return False
    config.set(VOLUME, raw.get(VOLUME, DEFAULT_VOLUME))
    config.set(MUTED, raw.get(MUTED, False))
    _bus().changed.emit(str(config.path))
    return True


def menu_config(pet):
    from .sprite_menu_facade import SpriteMenuFacade
    if isinstance(pet, SpriteMenuFacade):
        from .config import Config
        return Config(base=pet._shell._config.dir.parent,
                      instance_id=pet._shell.sprite_instance_id(pet.sprite))
    return pet.cfg


def semantic_stamp(config):
    """Retain disk-change revocation except volume/mute and slot ownership metadata.

    One read/hash per changed file, bounded 128-entry cache; no polling or logging
    of config contents. In-memory role/permission checks remain at their callers.
    """
    path = config.path
    try:
        stat = path.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        return None
    key = str(path)
    old = _semantic.get(key)
    if old and old[0] == signature:
        _semantic.move_to_end(key)
        return old[1]
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raise ValueError('Invalid config object')
        for name in (VOLUME, MUTED, 'user_customized'):
            raw.pop(name, None)
        result = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
    except (OSError, ValueError, AttributeError):
        result = signature  # Malformed/unreadable changes still revoke old tickets.
    _semantic[key] = (signature, result)
    while len(_semantic) > 128:
        _semantic.popitem(last=False)
    return result


class VolumeBinding(QObject):
    changed = Signal(int, bool)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.current = values(config)
        self.signature = self._signature()
        self.watcher = QFileSystemWatcher(self)
        if getattr(config, "path", None) is not None and config.path.parent.is_dir():
            self.watcher.addPath(str(config.path.parent))  # atomic replacements keep the directory
        self.watcher.directoryChanged.connect(self.refresh)
        _bus().changed.connect(self.refresh)

    def _signature(self):
        try:
            stat = self.config.path.stat()
            return stat.st_mtime_ns, stat.st_size
        except (OSError, AttributeError):
            return None

    def refresh(self, path=''):
        config_path = getattr(self.config, 'path', None)
        if path and config_path is not None and str(path) not in (str(config_path), str(config_path.parent)):
            return
        if config_path is not None and config_path.parent.is_dir() and str(config_path.parent) not in self.watcher.directories():
            self.watcher.addPath(str(config_path.parent))
        signature = self._signature()
        if config_path is not None and signature == self.signature:
            return
        self.signature = signature
        new = values(self.config)
        if new != self.current:
            self.current = new
            self.changed.emit(*new)
