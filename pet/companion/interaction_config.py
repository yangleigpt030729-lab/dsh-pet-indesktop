"""Independent opt-ins, separate from ordinary proactive frequency settings."""
DEFAULTS = {'head_touch_enabled': False, 'feeding_enabled': False}


def normalize_config(raw):
    raw = raw if isinstance(raw, dict) else {}
    return {k: raw[k] if isinstance(raw.get(k), bool) else v for k, v in DEFAULTS.items()}


def enabled(config, key):
    from .proactive_policy import policy
    _, runtime = policy(config.path, feature=key)
    return runtime if isinstance(runtime, bool) else normalize_config(config.get('companion_interaction'))[key]
