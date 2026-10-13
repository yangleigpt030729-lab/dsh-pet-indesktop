"""Small mouse/presentation adapters; Qt remains on the GUI thread."""
import hashlib
import json
import weakref
import shiboken6
from PySide6.QtCore import QPointF
from .touch_region import head_core_at
from .interaction_config import enabled


def manual_busy():
    from PySide6.QtWidgets import QApplication
    for win in QApplication.topLevelWidgets():
        if win.isVisible() and getattr(win, 'service', None) is not None:
            return True
    return False


class Target:
    def __init__(self, host, sprite=None):
        self.host_ref = weakref.ref(host)
        self.sprite_ref = weakref.ref(sprite) if sprite is not None else None
        self.key = ('overlay', id(host), id(sprite)) if sprite is not None else ('legacy', id(host))

    def config(self):
        host = self.host_ref()
        return SpriteInteractionConfig(host, self.sprite_ref()) if self.sprite_ref else host.cfg

    def identity(self):
        cfg = self.config()
        try:
            stamp = cfg.path.stat().st_mtime_ns
        except OSError:
            stamp = 0
        from .expression_style import context
        values = [str(cfg.dir), cfg.get('character'), cfg.get('companion_interaction'), cfg.chat_settings().to_dict(), stamp, context(cfg)]
        return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()

    def valid(self):
        host = self.host_ref()
        if host is None or not shiboken6.isValid(host):
            return False
        shell = getattr(getattr(host, '_instance', None), 'shell', None) if self.sprite_ref else getattr(host, 'companion_shell', None)
        if getattr(shell, '_quitting', False) or getattr(shell, '_companion_suspended', False):
            return False
        interpreter = (getattr(getattr(host, '_file_interpret_offer', None), '__self__', None)
                       if self.sprite_ref else getattr(host, '_file_interpret', None))
        if getattr(interpreter, '_state', None) in ('awaiting', 'running'):
            return False  # Consent/progress owns presentation, including a child's follower.
        if self.sprite_ref:
            sprite = self.sprite_ref()
            return bool(sprite is not None and shiboken6.isValid(sprite)
                        and shiboken6.isValid(host.overlay)
                        and sprite in host.overlay.sprites and host.overlay.isVisible()
                        and host._sprite_speech_visible(sprite) and not host._bubble_blocked(sprite)
                        and host._alert_current is None and not host._sticky_bubble_active)
        return bool(host.isVisible() and not host._closing and not host._bubble_suppressed
                    and host._alert_current is None and not host._sticky_bubble_active and not host._dragging)

    manual_busy = staticmethod(manual_busy)

    def present(self, text):
        if not self.valid():
            return False
        host = self.host_ref()
        if self.sprite_ref:
            sprite = self.sprite_ref()
            follower = host._bubble_for(sprite)
            if follower is None:
                return False  # Never redirect a destroyed child's AI response to its parent.
            before = follower.bubble.text_presentation_id
            shown = follower.show(text, 5000)
            return bool(shown and follower.bubble.text_was_presented(text, before))
        before = host._speech_bubble.text_presentation_id
        host.show_bubble(text, duration_ms=5000)
        return host._speech_bubble.text_was_presented(text, before)


def service(shell):
    if not getattr(shell, 'enable_chat', False):
        return None
    current = getattr(shell, 'companion_interactions', None)
    if current is None:
        from .interaction_service import InteractionService
        current = shell.companion_interactions = InteractionService()
    return current


def request(shell, kind, target, metadata=None):
    current = service(shell)
    if current is None:
        return False
    proactive = getattr(shell, 'companion_service', None)
    if proactive is not None:
        proactive.cancel()  # Explicit user events take priority over ordinary greetings.
    return current.request(kind, target, metadata)


def legacy_head(shell, win, point, press=None):
    if not getattr(shell, 'enable_chat', False) or not enabled(win.cfg, 'head_touch_enabled'):
        return False
    if win._is_transparent_at(point):
        return False
    probe = getattr(win, '_effects_probe_active', None)
    if callable(probe) and probe():
        return False
    rect = win._frame_draw_rect()
    clip = win.anim
    mirrored = win.facing == 'right' and clip not in getattr(win.lib, 'no_mirror', ())
    char = win.cfg.get('character')
    if not head_core_at(char, point, rect, mirrored) or not head_core_at(char, press or point, rect, mirrored):
        return False
    route_spin = getattr(win, '_effects_route_click_golden_spin', None)
    if callable(route_spin) and route_spin():
        return True  # Existing direct spin consumes the gesture without a second click.
    if win.clicks:
        win._cancel_move()
        win._start_squash()
        win._switch(win._pick(win.clicks))
    request(shell, 'head', Target(win))
    return True  # Busy/model failure still consumes this head click, never ordinary speech.


def overlay_head(shell, overlay, sprite, point, press):
    cfg = SpriteInteractionConfig(overlay, sprite)
    if not getattr(shell, 'enable_chat', False) or not enabled(cfg, 'head_touch_enabled'):
        return False
    local = QPointF(point)-sprite.pos
    if sprite.alpha_at(local) < 16 or abs(sprite._probe_angle)+abs(sprite._throw_angle) > 1e-6:
        return False
    rect = sprite._squashed_rect() if sprite._squash_progress is not None else sprite.rect()
    if not all(head_core_at(cfg.get('character'), p, rect, sprite._mirror_frame()) for p in (point, press)):
        return False
    overlay.behavior.on_sprite_clicked(sprite)
    sprite.squash()
    if callable(getattr(overlay.overlay, 'click_feedback', None)):
        overlay._sound.on_click(sprite)
    request(shell, 'head', Target(overlay, sprite))
    return True


def close(shell):
    current = getattr(shell, 'companion_interactions', None)
    if current:
        current.close()


class SpriteInteractionConfig:
    """Read cached per-slot settings and use its actual policy file identity."""
    def __init__(self, host, sprite):
        self.view = host._sprite_config(sprite)
        self.dir = host._config.dir
        self.instance_id = host.sprite_instance_id(sprite)
        self.path = self.dir / ('config-'+self.instance_id+'.json' if self.instance_id else 'config.json')

    def get(self, key, default=None):
        return self.view.get(key, default)

    def chat_settings(self):
        slot = getattr(self.view, '_slot_data', None)
        if isinstance(slot, dict) and isinstance(slot.get('chat'), dict):
            from ..chat.models import ChatSettings
            return ChatSettings.from_dict(slot['chat'])
        return self.view.chat_settings()

    def resolve_api_key(self, provider):
        return self.view.resolve_api_key(provider)


def bind_overlay(overlay):
    overlay.overlay._companion_head_click = lambda sprite, point, press: overlay_head(
        getattr(overlay._instance, 'shell', None), overlay, sprite, point, press)


def offer_feeding(shell, target, metadata):
    if shell is None or not getattr(shell, 'enable_chat', False):
        return False
    if not enabled(target.config(), 'feeding_enabled'):
        return False
    current = service(shell)
    proactive = getattr(shell, 'companion_service', None)
    if proactive:
        proactive.cancel()
    current.offer_feeding(target, metadata)
    return True
