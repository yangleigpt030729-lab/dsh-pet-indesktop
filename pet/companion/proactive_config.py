"""Opt-in settings. This module deliberately has no Qt/chat dependencies."""
import re

DEFAULTS = dict(enabled=False, greetings=True, break_reminders=True,
                water_reminders=True, scheduled_reminders=True, use_memory=True,
                daily_limit=10, min_interval_minutes=30, quiet_hours=None,
                avoid_semantic_repeats=True)


def normalize_config(raw):
    raw = raw if isinstance(raw, dict) else {}
    result = DEFAULTS.copy()
    for key, default in DEFAULTS.items():
        value = raw.get(key, default)
        if isinstance(default, bool):
            result[key] = value if isinstance(value, bool) else default
    for key, lo, hi in [('daily_limit', 0, 10), ('min_interval_minutes', 30, 180)]:
        value = raw.get(key, DEFAULTS[key])
        result[key] = max(lo, min(hi, value)) if type(value) is int else DEFAULTS[key]
    hours = raw.get('quiet_hours')
    if isinstance(hours, (list, tuple)) and len(hours) == 2 and all(
            isinstance(t, str) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', t) for t in hours):
        result['quiet_hours'] = list(hours)
    return result
