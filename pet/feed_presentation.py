"""One feeding handoff: content consent wins; fun feedback uses metadata only."""
import weakref
import shiboken6


def offer(interpret, paths, resume, *, target=None):
    if not callable(interpret):
        return False
    from .file_interpret import FileInterpretController
    owner = getattr(interpret, '__self__', None)
    if isinstance(owner, FileInterpretController):
        if owner._state in ('running', 'awaiting'):
            return True  # Preserve the existing interpretation/progress bubble.
        return owner.offer(paths, on_decline=resume, target=target)
    return interpret(paths) is True  # Preserve external one-argument seam.


class OverlayInterpretTarget:
    def __init__(self, shell, sprite):
        from .companion.interaction_runtime import Target
        self.actor = Target(shell, sprite)
        self.ref = weakref.ref(sprite)
        self.library = id(sprite.library)
        self.shell_ref = weakref.ref(shell)
        self.character = self.cfg.get('character')
        self._alert = False

    @property
    def cfg(self):
        return self.actor.config()

    def valid(self):
        shell, sprite = self.shell_ref(), self.ref()
        return bool(shell is not None and shiboken6.isValid(shell) and shiboken6.isValid(shell.overlay) and sprite is not None
                    and shiboken6.isValid(sprite) and sprite in shell.overlay.sprites
                    and id(sprite.library) == self.library and self.cfg.get('character') == self.character
                    and not getattr(getattr(shell._instance, 'shell', None), '_quitting', False))

    def show_alert(self, text, **kwargs):
        if not self.valid():
            return False
        shell, sprite = self.shell_ref(), self.ref()
        if sprite is shell.sprite:
            return shell.show_alert(text, **kwargs)
        follower = shell._bubble_for(sprite)
        self._alert = True
        return follower.show(text, 0, subtitle=kwargs.get('subtitle', ''), sticky=True, buttons=kwargs.get('buttons'))

    def resolve_alert(self, alert_id):
        if not self.valid():
            return
        shell, sprite = self.shell_ref(), self.ref()
        if sprite is shell.sprite:
            shell.resolve_alert(alert_id)
        elif self._alert:
            shell._hide_bubble_for_sprite(sprite)
            self._alert = False

    def show_bubble(self, text, duration_ms=3200, **kwargs):
        if self.valid():
            return self.shell_ref()._show_bubble_text_for(self.ref(), text, duration_ms)
