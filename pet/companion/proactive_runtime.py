"""AppShell adapter; lazy chat imports preserve the no-chat distribution."""
import sys
from .proactive_config import normalize_config
from .proactive_schedule import Snapshot


def host(shell):
    overlay = getattr(shell, '_overlay_shell', None)
    candidates = [overlay] if overlay is not None else [getattr(i, 'win', None) for i in getattr(shell, 'instances', [])]
    for target in candidates:
        if target is None:
            continue
        try:
            if target.can_show_proactive_bubble():
                return target
        except (RuntimeError, AttributeError):
            continue
    return None


def snapshot(shell):
    from PySide6.QtWidgets import QApplication
    from .. import platform_win, vision
    manual = False
    for window in QApplication.topLevelWidgets():
        try:
            if window.isVisible() and getattr(window, 'service', None) is not None:
                manual = True
                break
        except RuntimeError:
            continue
    return Snapshot(visible=host(shell) is not None, typing=manual,
                    fullscreen=platform_win._fg_fullscreen_win32() if sys.platform == 'win32' else False,
                    suspended=bool(getattr(shell, '_companion_suspended', False)),
                    quitting=bool(getattr(shell, '_quitting', False) or getattr(shell, '_session_end_done', False)),
                    idle_seconds=vision.get_system_idle_seconds())


def present(shell, text):
    if not snapshot(shell).allowed:
        return False
    target = host(shell)
    return target.try_show_bubble(text) if target is not None else False


def sync(shell):
    service = getattr(shell, 'companion_service', None)
    if not getattr(shell, 'enable_chat', False):
        if service:
            service.close()
        return
    cfg = normalize_config(shell.config.get('proactive_chat'))
    if service is None and cfg['enabled']:
        from .proactive_service import ProactiveService
        service = ProactiveService(shell.config, lambda: snapshot(shell), lambda text: present(shell, text))
        shell.companion_service = service
        install_interaction_filter(shell, service)
    if service:
        service.apply_config()
        register_session(shell)


def register_session(shell):
    """Legacy needs its own WTS registration; overlay already owns registration."""
    if sys.platform != 'win32' or getattr(shell, '_overlay_shell', None) is not None:
        return
    watcher = getattr(shell, '_session_watcher', None)
    target = getattr(shell, 'win', None)
    if watcher is not None and target is not None and normalize_config(shell.config.get('proactive_chat'))['enabled']:
        try:
            watcher.register_session_notifications(target.winId())
        except RuntimeError:
            pass


def close(shell):
    service = getattr(shell, 'companion_service', None)
    if service:
        service.close()


def suspend(shell, active, _reason=''):
    shell._companion_suspended = bool(active)
    service = getattr(shell, 'companion_service', None)
    if service:
        service.cancel()
        service.scheduler.activity = 0
        service.scheduler.last_tick = None


def install_interaction_filter(shell, service):
    from PySide6.QtCore import QObject, QEvent
    from PySide6.QtWidgets import QApplication
    class InteractionFilter(QObject):
        def eventFilter(self, obj, event):
            if event.type() in (QEvent.Type.KeyPress, QEvent.Type.FocusIn, QEvent.Type.MouseButtonPress):
                if service.busy and snapshot(shell).typing:
                    service.cancel()
            return False
    service.interaction_filter = InteractionFilter(service)
    QApplication.instance().installEventFilter(service.interaction_filter)
