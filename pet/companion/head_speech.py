"""Two accompaniment opt-ins reuse the original reader, queue and player.

The historical module/key remain compatible. A ticket belongs to one accepted
bubble generation and is checked again by the existing audio channel before play.
"""
import time
import json
import weakref
import shiboken6
from .interaction_config import enabled
from .proactive_policy import policy, set_enabled

PASSIVE = 'self_talk_speak_enabled'
ACTIVE = 'proactive_bubble_speak_enabled'


def speech_enabled(config, *, active=False):
    feature = ACTIVE if active else PASSIVE
    path = getattr(config, 'path', None)
    runtime = policy(path, feature=feature)[1] if path is not None else None
    # A runtime denial is immediate even when save fails. An old opt-in cannot
    # override a persisted opt-out from another settings process/config refresh.
    return runtime is not False and bool(config.get(feature, False))


def permission_stamp(config, *, active=False):
    """GUI-only permission generations; no SQLite or credential access."""
    from .memory_context import _runtime_policy
    path = config.path
    return (policy(path, feature=ACTIVE if active else PASSIVE)[0],
            policy(path, feature='head_touch_enabled')[0],
            policy(path, feature='feeding_enabled')[0], policy(path)[0], _runtime_policy(path)[0])


def save_toggle(dialog, value, *, active=False):
    config = dialog.config
    feature = ACTIVE if active else PASSIVE
    set_enabled(config.path, value, feature=feature)
    config.reload()
    config.set(feature, value)
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
    for cfg in configs:
        chat = getattr(shell, 'enable_chat', False)
        passive = speech_enabled(cfg) and (cfg.get('click_show_self_talk', False)
            or cfg.get('self_talk_enabled', False)
            or (chat and (enabled(cfg, 'head_touch_enabled') or enabled(cfg, 'feeding_enabled'))))
        active = speech_enabled(cfg, active=True) and (cfg.get('todo_reminder_enabled', True)
            or (chat and (cfg.get('proactive_chat') or {}).get('enabled', False)))
        if passive or active:
            return True
    return False


def target_for_host(host):
    from .interaction_runtime import Target
    if hasattr(host, '_shell') and hasattr(host, '_sprite'):
        return Target(host._shell, host._sprite)
    return Target(host, host.sprite) if hasattr(host, 'overlay') and hasattr(host, 'sprite') else Target(host)


def speak_displayed(host, text, *, active=False, valid=None):
    speak_target(target_for_host(host), text, valid or (lambda: True), active=active)


def speak_target(target, text, valid, *, active=False):
    request = speech_request(target, text, valid, active=active)
    if request is not None:
        request()


def speech_identity(config):
    # Ordinary self-talk also ships without chat. Do not instantiate ChatSettings.
    keys = ('character', 'chat', 'dialogue_mode', 'dialogue_phrases', 'companion_interaction',
            'self_talk_enabled', 'click_show_self_talk', 'proactive_chat', 'todo_reminder_enabled',
            'voice_chime_voice', 'voice_chime_rate', 'voice_chime_pitch', 'voice_chime_volume')
    try:
        stamp = config.path.stat().st_mtime_ns
    except OSError:
        stamp = 0
    return json.dumps([str(config.path), stamp, [config.get(k) for k in keys]], sort_keys=True)


def speech_request(target, text, valid, *, active=False):
    """Only an exact visible text receipt can create a revocable speech request."""
    if not valid() or not target.valid():
        return
    config = target.config()
    if not speech_enabled(config, active=active):
        return
    host = target.host_ref()
    sprite = target.sprite_ref() if target.sprite_ref else None
    follower = host._bubble_for(sprite) if sprite is not None else None
    bubble = follower.bubble if follower is not None else getattr(host, '_speech_bubble', None)
    if bubble is None or not bubble.text_was_presented(text, bubble.text_presentation_id-1):
        return
    receipt = bubble.text_presentation_id
    if getattr(bubble, '_companion_spoken_receipt', None) == receipt:
        return
    # Install one weak listener per bubble, not one listener per interaction.
    if not hasattr(bubble, '_companion_speech_epoch'):
        bubble._companion_speech_epoch = 0
        ref = weakref.ref(bubble)
        def hidden():
            current = ref()
            if current is not None:
                current._companion_speech_epoch += 1
        bubble.hidden_signal.connect(hidden)
    epoch = bubble._companion_speech_epoch
    bubble_ref = weakref.ref(bubble)
    identity, consent = speech_identity(config), permission_stamp(config, active=active)
    expires = time.monotonic()+30
    def current():
        b = bubble_ref()
        return bool(b is not None and shiboken6.isValid(b) and valid() and target.valid()
            and time.monotonic() < expires and speech_identity(target.config()) == identity
            and permission_stamp(target.config(), active=active) == consent
            and speech_enabled(target.config(), active=active) and b._companion_speech_epoch == epoch
            and b.text_presentation_id == receipt and b.text_was_presented(text, receipt-1))
    if not current():
        return
    reader_host = host
    if sprite is not None and sprite is not host.sprite:
        reader_host = host._self_talk_hosts.get(sprite)
    speaker = getattr(reader_host, 'on_self_talk_speak', None)
    if not callable(speaker):
        return
    def enqueue():
        if not current() or getattr(bubble, '_companion_spoken_receipt', None) == receipt:
            return
        bubble._companion_spoken_receipt = receipt
        try:
            speaker(text, valid=current, config=config)
        except Exception:
            import logging
            logging.getLogger('dsh-pet-standalone').warning('陪伴朗读失败；保留文字气泡')
    return enqueue
