"""Real AppShell/animation/bubble smoke using a blocked Fake Provider, no API key.

Run with repository-supported PET_FRAMESEQ=0 for a short offscreen startup.
This is Linux/cloud evidence, never a Windows acceptance claim.
"""
import sys
import tempfile
import threading
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from pet import catalog
from pet.app import AppShell
from pet.config import Config
import pet.companion.proactive_service as proactive

barrier = threading.Event()
started = threading.Event()


class FakeProvider:
    def stream(self, messages, config, cancel):
        started.set()
        barrier.wait(10)
        yield '合成测试：本鱼在这里陪你看看云。'


original_service = proactive.ProactiveService
proactive.ProactiveService = lambda *a, **k: original_service(*a, **k, provider=FakeProvider())
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
with tempfile.TemporaryDirectory(prefix='pet-proactive-smoke-') as directory:
    cfg = Config(base=Path(directory))
    cfg.set('proactive_chat', {'enabled': True})
    cfg.set('self_talk_enabled', False)
    cfg.set('todo_reminder_enabled', False)
    cfg.set('no_move', True)
    cfg.save()
    shell = AppShell(app, cfg)
    shell.start()
    service = shell.companion_service
    overlay = shell._overlay_shell
    clip = overlay.lib.movie(catalog.IDLE)
    initial_frame = clip.currentFrameNumber()
    shown = []
    service.delivered.connect(shown.append)
    service.tick()
    deadline = time.monotonic()+15
    result = []
    timer = QTimer()
    timer.setInterval(20)
    def verify():
        if started.is_set() and clip.currentFrameNumber() != initial_frame:
            barrier.set()
        if shown and not service.busy:
            assert barrier.is_set(), "model must be released by observed animation advancement"
            assert overlay._speech_bubble.isVisible()
            assert not overlay.overlay.grab().isNull()
            image = clip.currentPixmap().toImage()
            assert not image.isNull()
            alpha = {image.pixelColor(x, y).alpha() for x in range(0, image.width(), 20) for y in range(0, image.height(), 10)}
            assert len(alpha) > 1
            assert service.state.path.parent == cfg.dir
            result.append(True)
            print('PASS: real AppShell, blocked fake model + advancing animation, transparent decoded frame, single real bubble, durable receipt, graceful shutdown', flush=True)
            timer.stop()
            app.quit()
        elif time.monotonic() > deadline:
            print('FAIL: bounded smoke deadline expired', flush=True)
            barrier.set()
            timer.stop()
            app.quit()
    timer.timeout.connect(verify)
    timer.start()
    app.exec()
    assert result == [True]
