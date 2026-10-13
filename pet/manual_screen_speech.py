"""Manual screen-result receipt and speech; no automatic capture policy changes."""
import weakref
import json
import shiboken6
from PySide6.QtCore import QObject, QTimer, QEvent
from .companion.interaction_runtime import Target
from .companion.head_speech import speak_target

class ManualScreenRequest(QObject):
    def __init__(self, host, sprite=None):
        super().__init__(host)
        self.owner = weakref.ref(host)
        self.target = Target(host, sprite)
        self.identity = self._identity()
        self.stage = 'cue'
        surface = host.overlay if sprite is not None else host
        surface.installEventFilter(self)
        if sprite is not None:
            sprite.destroyed.connect(self.cancel)
            host._bubble_for(sprite).bubble.hidden_signal.connect(self._sprite_hidden)
        self.cancelled = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.expire)
        self.timer.start(120000)  # network-stage watchdog, not an audio duration cap

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Hide, QEvent.Type.Close):
            self.cancel()
        return False

    def _sprite_hidden(self):
        host, sprite = self.owner(), self.target.sprite_ref()
        if host is not None and shiboken6.isValid(host) and sprite is not None and shiboken6.isValid(sprite):
            if not host._sprite_speech_visible(sprite):
                self.cancel()

    def _identity(self):
        cfg = self.target.config()
        return (str(cfg.path), cfg.get("character"), json.dumps(cfg.chat_settings().to_dict(), sort_keys=True))

    def valid(self):
        host = self.owner()
        return (not self.cancelled and host is not None and shiboken6.isValid(host)
                and getattr(host, '_manual_screen_request', None) is self
                and self.target.valid() and self._identity() == self.identity)

    def cancel(self):
        self.cancelled = True
        self.timer.stop()

    def expire(self):
        self.cancel()
        host = self.owner()
        if host is not None and shiboken6.isValid(host) and getattr(host, '_manual_screen_request', None) is self:
            host._look_busy = False

    def present(self, text, duration, stage, *, speak=True):
        if not self.valid():
            return False
        self.stage = stage
        if stage == 'final':
            self.timer.stop()
        host = self.owner()
        sprite = self.target.sprite_ref() if self.target.sprite_ref else None
        bubble = host._bubble_for(sprite).bubble if sprite is not None else host._speech_bubble
        before = bubble.text_presentation_id
        if sprite is None:
            host.show_bubble(text, duration_ms=duration)
        else:
            host._show_bubble_text_for(sprite, text, duration)
        if not bubble.text_was_presented(text, before):
            return False
        if speak:
            speak_target(self.target, text, lambda: self.valid() and self.stage == stage, active=True)
        return True


def begin(host, sprite=None):
    if not shiboken6.isValid(host):
        return None  # old non-QObject integration seam; no speech without a real receipt
    old = getattr(host, '_manual_screen_request', None)
    if old is not None:
        old.cancel()
        old.deleteLater()
    request = ManualScreenRequest(host, sprite)
    host._manual_screen_request = request
    return request


def receive(host, payload):
    request, text, user_text, error = payload
    if getattr(host, '_manual_screen_request', None) is not request:
        return
    host._on_look_done(text, user_text, error)
