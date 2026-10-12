"""Real QMenu tracking loop -> real modeless settings, both render topologies."""
import pytest
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu

from pet.app import PetInstance
from pet.config import Config
from pet.modern_settings_dialog import ModernSettingsDialog
from pet.overlay_shell import OverlayShell
from pet.pet_sprite import PetSprite
from pet.window import PetWindow
from tests.test_companion_chat import wait
from tests.test_context_menu_lifecycle import FakeLibrary
from tests.test_settings_process_isolation import _bare_shell
from tests.test_sprite_menu_facade import RichLibrary
from tests.test_overlay_window_capabilities import FakeScreen


@pytest.fixture
def settings_host(tmp_path, monkeypatch):
    from pet import modern_settings_dialog as settings
    monkeypatch.setattr(settings.autostart_mod, 'is_enabled', lambda: False)
    app = QApplication.instance() or QApplication([])
    config = Config(base=tmp_path/'acceptance')
    config.set('settings_process_isolation', False)
    config.save()
    shell = _bare_shell(config)
    shell.enable_chat = True
    shell.instance = PetInstance(shell, config)
    shell._instances = [shell.instance]
    shell.precache_self_talk_voice = lambda *a: None
    shell._apply_external_config_change = lambda: config.reload()
    yield app, shell, config
    for dialog in app.topLevelWidgets():
        if isinstance(dialog, ModernSettingsDialog) and dialog.config.dir == config.dir:
            dialog.close()
            dialog.deleteLater()
            QCoreApplication.sendPostedEvents(dialog, QEvent.Type.DeferredDelete)
    shell._teardown_config_watcher()


def arm_settings_action(menu, made):
    """Trigger while visible, then let the actual QMenu.exec nested loop return."""
    actions = [a for m in [menu, *menu.findChildren(QMenu)] for a in m.actions()
               if a.text() == '桌宠设置']
    assert len(actions) == 1
    made.append(menu)
    menu.aboutToShow.connect(lambda: QTimer.singleShot(0, menu, actions[0].trigger))
    QTimer.singleShot(10000, menu, menu.close)  # Fail boundedly if dispatch breaks.


def overlay_for(shell, config):
    lib = RichLibrary()
    shell.instance._create_library = lambda cid: RichLibrary()
    overlay = OverlayShell(QApplication.instance(), shell.instance,
                          screen=FakeScreen((0, 0, 1920, 1080), (0, 0, 1920, 1040)),
                          sprite_factory=lambda library, pos, scale: PetSprite(library, pos=pos, scale=scale))
    overlay.lib = lib
    overlay.sprite.library = lib
    overlay.sprite.bind_clip('idle1')
    overlay.sprite._rebuild_pixmap()
    return overlay


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('process_failure', [False, True])
def test_right_click_settings_then_island_and_reopen(settings_host, monkeypatch, topology, process_failure):
    app, shell, cfg = settings_host
    if process_failure:
        from PySide6.QtCore import QProcess
        cfg.set('settings_process_isolation', True)
        monkeypatch.setattr(QProcess, 'startDetached', staticmethod(lambda *a: (False, 0)))
    made = []
    if topology == 'legacy':
        host = PetWindow(FakeLibrary(), cfg)
        shell.instance.win = host
        host.on_open_modern_settings = shell.instance.open_modern_settings
        original = host._exec_context_menu
        def execute(menu, pos):
            arm_settings_action(menu, made)
            original(menu, pos)
        monkeypatch.setattr(host, '_exec_context_menu', execute)
        trigger = lambda: host._show_context_menu(QPoint(100, 100))
    else:
        host = overlay_for(shell, cfg)
        original = host.overlay._full_menu_builder
        def build(sprite):
            menu = original(sprite)
            arm_settings_action(menu, made)
            return menu
        host.overlay._full_menu_builder = build
        def trigger():
            point = host.sprite.rect().center()
            host.overlay.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse,
                                                           point, host.overlay.mapToGlobal(point)))
    try:
        trigger()
        # Targeted DeferredDelete only: do not destroy another test's objects.
        QCoreApplication.sendPostedEvents(made[-1], QEvent.Type.DeferredDelete)
        wait(app, lambda: shell.instance.modern_settings_dialog is not None)
        dialog = shell.instance.modern_settings_dialog
        wait(app, dialog.isVisible)
        assert dialog.config is cfg and dialog.include_ai
        assert not shiboken6.isValid(made[-1])
        shell._open_settings_from_island()
        assert shell.instance.modern_settings_dialog is dialog
        dialog.close()
        assert shell.instance.modern_settings_dialog is None
        trigger()
        QCoreApplication.sendPostedEvents(made[-1], QEvent.Type.DeferredDelete)
        wait(app, lambda: shell.instance.modern_settings_dialog is not None)
        assert shell.instance.modern_settings_dialog is not dialog
        assert shell.instance.modern_settings_dialog.isVisible()
    finally:
        host.close() if topology == 'legacy' else host.stop()


def test_isolated_process_receives_acceptance_base_and_slot(settings_host, monkeypatch):
    from PySide6.QtCore import QProcess
    app, shell, cfg = settings_host
    cfg.set('settings_process_isolation', True)
    child = PetInstance(shell, Config(base=cfg.dir.parent, instance_id='slot-2'), slot_id=2)
    calls = []
    monkeypatch.setattr(QProcess, 'startDetached', staticmethod(
        lambda *args: calls.append(args) or (True, 4242)))
    child.open_modern_settings()
    assert child.modern_settings_dialog is None
    args = calls[0][1]
    assert args[args.index('--instance')+1] == 'slot-2'
    assert args[args.index('--settings-base')+1] == str(cfg.dir.parent.resolve())
    shell._companion_acceptance_fake = True
    calls.clear()
    assert shell._launch_settings_process(child)
    assert '--settings-fake' in calls[0][1]


def test_overlay_child_settings_uses_slot_config_and_reopens(settings_host):
    app, shell, cfg = settings_host
    host = overlay_for(shell, cfg)
    try:
        host.spawn_pet()
        child = host._spawned[0]
        identity = host.sprite_instance_id(child)
        original = cfg.path.read_bytes()
        assert host.open_settings_for(child)
        dialogs = [d for d in app.topLevelWidgets() if isinstance(d, ModernSettingsDialog)
                   and d.config.instance_id == identity and d.config.dir == cfg.dir]
        assert len(dialogs) == 1 and dialogs[0].isVisible()
        dialog = dialogs[0]
        assert dialog.config.path.name == f'config-{identity}.json'
        assert dialog.config.get('character') == host._sprite_config(child).get('character')
        assert host.open_settings_for(child)
        assert len([d for d in app.topLevelWidgets() if isinstance(d, ModernSettingsDialog)
                    and d.isVisible() and d.config.instance_id == identity]) == 1
        dialog.close()
        assert cfg.path.read_bytes() == original
        assert host.open_settings_for(child)
        assert any(d is not dialog and d.isVisible() and d.config.instance_id == identity
                   for d in app.topLevelWidgets() if isinstance(d, ModernSettingsDialog))
    finally:
        host.clear_spawned_pets()
        host.stop()
        host.overlay.close()


def test_pending_dialog_presentation_drops_when_destroyed(settings_host, monkeypatch):
    app, shell, cfg = settings_host
    shell.instance.open_modern_settings()
    dialog = shell.instance.modern_settings_dialog
    dialog.hide()
    menu = QMenu()
    menu.addAction('保持菜单打开')
    menu.popup(QPoint(10, 10))
    assert QApplication.activePopupWidget() is menu
    errors = []
    import sys
    monkeypatch.setattr(sys, 'excepthook', lambda kind, value, tb: errors.append(value))
    shell.instance._present_dialog(dialog)
    assert dialog is not None and not dialog.isVisible()
    dialog.close()
    QCoreApplication.sendPostedEvents(dialog, QEvent.Type.DeferredDelete)
    menu.close()
    timer = QTimer()
    elapsed = []
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: elapsed.append(True))
    timer.start(200)
    wait(app, lambda: elapsed)
    assert errors == []
    assert shell.instance.modern_settings_dialog is None
    menu.deleteLater()
    QCoreApplication.sendPostedEvents(menu, QEvent.Type.DeferredDelete)


def test_overlay_deferred_callback_drops_after_owner_destroyed(settings_host):
    app, shell, cfg = settings_host
    host = overlay_for(shell, cfg)
    calls = []
    menu = QMenu()
    menu._deferred_callbacks = [lambda: calls.append(True)]
    host.overlay._dispatch_deferred_menu_callbacks(menu)
    host.overlay.deleteLater()
    QCoreApplication.sendPostedEvents(host.overlay, QEvent.Type.DeferredDelete)
    app.processEvents()
    assert calls == []
    menu.deleteLater()
    QCoreApplication.sendPostedEvents(menu, QEvent.Type.DeferredDelete)


def test_settings_child_process_preserves_base_slot_and_fake(tmp_path):
    import os
    import subprocess
    import sys
    base = tmp_path/'acceptance'
    cfg = Config(base=base, instance_id='slot-2')
    cfg.set('character', 'dafeiyu')
    cfg.save()
    code = '''
import sys
import keyring
from PySide6.QtCore import QTimer
import pet.__main__ as entry
import pet.modern_settings_dialog as settings
def forbidden(*a, **k):
    raise AssertionError('Settings child accessed real credentials')
keyring.get_password = keyring.set_password = forbidden
original = settings.ModernSettingsDialog
class Dialog(original):
    def show(self):
        super().show()
        from pet.chat.service import ChatService
        from pet.chat.models import SecretStore
        assert type(ChatService().provider).__name__ == 'FakeProvider'
        assert SecretStore.get('synthetic-ref') == ''
        assert self.config.instance_id == 'slot-2'
        assert str(self.config.dir.parent) == sys.argv[sys.argv.index('--settings-base')+1]
        assert 'pet.app' not in sys.modules
        print('PASS: real standalone settings with isolated slot and Fake Provider', flush=True)
        QTimer.singleShot(0, self, self.close)
settings.ModernSettingsDialog = Dialog
raise SystemExit(entry._run_settings())
'''
    result = subprocess.run([sys.executable, '-X', 'utf8', '-c', code, '--settings',
                             '--settings-base', str(base), '--instance', 'slot-2', '--settings-fake'],
                            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                            capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS: real standalone settings' in result.stdout
    assert not (cfg.dir/'settings.lock').exists()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
def test_right_click_isolated_settings_launches_once_while_pending(settings_host, monkeypatch, topology):
    from PySide6.QtCore import QProcess
    app, shell, cfg = settings_host
    cfg.set('settings_process_isolation', True)
    calls = []
    monkeypatch.setattr(QProcess, 'startDetached', staticmethod(lambda *a: calls.append(a) or (True, 4242)))
    made = []
    if topology == 'overlay':
        host = overlay_for(shell, cfg)
        builder = host.overlay._full_menu_builder
        def build(sprite):
            menu = builder(sprite)
            arm_settings_action(menu, made)
            return menu
        host.overlay._full_menu_builder = build
        trigger = lambda: host.overlay._exec_full_menu_at(host.overlay.mapToGlobal(host.sprite.rect().center()))
    else:
        host = PetWindow(FakeLibrary(), cfg)
        shell.instance.win = host
        host.on_open_modern_settings = shell.instance.open_modern_settings
        execute = host._exec_context_menu
        def run(menu, pos):
            arm_settings_action(menu, made)
            execute(menu, pos)
        host._exec_context_menu = run
        trigger = lambda: host._show_context_menu(QPoint(100, 100))
    try:
        trigger()
        QCoreApplication.sendPostedEvents(made[-1], QEvent.Type.DeferredDelete)
        wait(app, lambda: calls)
        assert shell.instance.modern_settings_dialog is None
        assert '--settings-base' in calls[0][1]
        trigger()
        QCoreApplication.sendPostedEvents(made[-1], QEvent.Type.DeferredDelete)
        completed = []
        QTimer.singleShot(0, lambda: completed.append(True))
        wait(app, lambda: completed)
        assert len(calls) == 1
    finally:
        host.close() if topology == 'legacy' else host.stop()
