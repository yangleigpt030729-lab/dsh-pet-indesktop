"""Measure real modeless settings lifecycles and isolated Fake chat initialization.

No pet animation is started. Use QT_QPA_PLATFORM=offscreen for headless runs.
Temporary configuration and synthetic Providers never use production credentials.
"""
import sys, tempfile, time, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psutil
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from pet.app import AppShell
from scripts.run_companion_acceptance import configure, install_fake_chat
from pet.chat.service import ChatService
from pet.modern_settings_dialog import ModernSettingsDialog
install_fake_chat()
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
with tempfile.TemporaryDirectory() as directory:
    cfg = configure(Path(directory))
    cfg.set('click_sound_enabled', False)
    cfg.set('collision_sound_enabled', False)
    cfg.set('todo_reminder_enabled', False)
    cfg.set('self_talk_enabled', False)
    cfg.save()
    shell = AppShell(app, cfg)
    samples = []
    retained = []
    rss = []
    process = psutil.Process()
    for n in range(20):
        start = time.perf_counter()
        shell.instance.open_modern_settings()
        dialog = shell.instance.modern_settings_dialog
        assert dialog.isVisible()
        samples.append((time.perf_counter()-start)*1000)
        dialog.close()
        QCoreApplication.sendPostedEvents(dialog, QEvent.Type.DeferredDelete)
        app.processEvents()
        assert not shiboken6.isValid(dialog)
        retained.append(sum(isinstance(w, ModernSettingsDialog) for w in app.topLevelWidgets()))
        rss.append(process.memory_info().rss/1024/1024)
    costs = []
    for n in range(100):
        start = time.perf_counter()
        service = ChatService()
        costs.append((time.perf_counter()-start)*1000)
        service.shutdown()
        service.deleteLater()
        QCoreApplication.sendPostedEvents(service, QEvent.Type.DeferredDelete)
    print(f'opens n=20 cold_ms={samples[0]:.3f} warm_median_ms={statistics.median(samples[1:]):.3f} warm_max_ms={max(samples[1:]):.3f}')
    print(f'dialogs_retained={retained} rss_after_warm_mib={rss[4]:.3f} rss_last_mib={rss[-1]:.3f}')
    print(f'fake_chat_init n=100 median_ms={statistics.median(costs):.3f} max_ms={max(costs):.3f}')
    shell._teardown_config_watcher()
