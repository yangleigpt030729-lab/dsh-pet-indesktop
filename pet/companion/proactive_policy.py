"""Immediate in-process opt-out survives a failed settings save."""
from threading import Lock

_lock = Lock()
_policies = {}


def policy(path, *, feature=None):
    with _lock:
        key = (str(path), feature) if feature else str(path)
        return _policies.get(key, (0, None))


def set_enabled(path, enabled, *, feature=None):
    with _lock:
        key = (str(path), feature) if feature else str(path)
        generation = _policies.get(key, (0, None))[0]
        _policies[key] = (generation+1, enabled)
