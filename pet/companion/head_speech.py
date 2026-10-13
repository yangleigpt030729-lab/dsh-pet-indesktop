"""Reuse the click reader; guarded requests never create another TTS channel."""
from .interaction_config import enabled
from .proactive_policy import policy, set_enabled


def speech_enabled(config):
    path = getattr(config, 'path', None)
    runtime = policy(path, feature='self_talk_speak_enabled')[1] if path is not None else None
    return runtime if isinstance(runtime, bool) else bool(config.get('self_talk_speak_enabled', False))


def permission_stamp(config):
    """GUI-only permission generations; no SQLite or credential access."""
    from .memory_context import _runtime_policy
    path = config.path
    return (policy(path, feature='self_talk_speak_enabled')[0],
            policy(path, feature='head_touch_enabled')[0], _runtime_policy(path)[0])


def save_toggle(dialog, value):
    config = dialog.config
    set_enabled(config.path, value, feature='self_talk_speak_enabled')
    config.set('self_talk_speak_enabled', value)
    if not config.save():
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(dialog, '朗读设置暂未保存', '当前进程已采用此选择，请检查目录权限后重新保存；重启前确认保存成功。')


def wanted(shell):
    configs = [shell.config]
    configs += [i.config for i in getattr(shell, '_instances', []) if i.config is not shell.config]
    overlay = getattr(shell, '_overlay_shell', None)
    if overlay is not None:
        from .interaction_runtime import SpriteInteractionConfig
        configs += [SpriteInteractionConfig(overlay, sprite) for sprite in getattr(overlay, '_spawned', ())]
    return any(speech_enabled(cfg) and (cfg.get('click_show_self_talk', False)
               or (getattr(shell, 'enable_chat', False) and enabled(cfg, 'head_touch_enabled'))) for cfg in configs)


def speak_target(target, text, valid):
    from ..window_alerts import speak_click_self_talk
    if not valid():
        return
    host = target.host_ref()
    if target.sprite_ref:
        sprite = target.sprite_ref()
        host = host if sprite is host.sprite else host._self_talk_hosts.get(sprite)
    if host is not None:
        speak_click_self_talk(host, text, valid=valid, config=target.config())
