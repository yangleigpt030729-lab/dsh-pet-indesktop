"""Opt-in settings. This module deliberately has no Qt/chat dependencies."""
import re
MAX_DAILY_LIMIT = 9999

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
    for key, lo, hi in [('daily_limit', 1, MAX_DAILY_LIMIT), ('min_interval_minutes', 1, 99)]:
        value = raw.get(key, DEFAULTS[key])
        result[key] = max(lo, min(hi, value)) if type(value) is int else DEFAULTS[key]
    backup = raw.get('legacy_ranges', {})
    backup = {k: backup[k] for k in ('daily_limit', 'min_interval_minutes')
              if isinstance(backup, dict) and type(backup.get(k)) is int}
    needs_review = raw.get('range_review') is True
    for key, rejected in [('daily_limit', lambda n: n <= 0),
                          ('min_interval_minutes', lambda n: n > 99)]:
        if type(raw.get(key)) is int and rejected(raw[key]):
            backup[key] = raw[key]
            needs_review = True
    if backup:
        result['legacy_ranges'] = backup
        result['range_review'] = needs_review
    if needs_review:
        result['enabled'] = False  # Never increase a legacy user's requests silently.
    hours = raw.get('quiet_hours')
    if isinstance(hours, (list, tuple)) and len(hours) == 2 and all(
            isinstance(t, str) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', t) for t in hours):
        result['quiet_hours'] = list(hours)
    return result
