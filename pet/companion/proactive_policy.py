"""Immediate in-process opt-out survives a failed settings save."""
from threading import Lock

_lock = Lock()
_policies = {}


def policy(path):
    with _lock:
        return _policies.get(str(path), (0, None))


def set_enabled(path, enabled):
    with _lock:
        generation = _policies.get(str(path), (0, None))[0]
        _policies[str(path)] = (generation+1, enabled)
