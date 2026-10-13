"""Real application/assets, local fallback and original drop UI; no network mocking.

Run with QT_QPA_PLATFORM=offscreen and PET_FRAMESEQ=0 for cloud evidence.
Chat configuration is disabled in the temporary directory, so no key or online
provider is used. This is never a Windows audio or DeepSeek acceptance result.
"""
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer, QPointF
from PySide6.QtWidgets import QApplication
from pet.app import AppShell
from pet.config import Config
from pet.companion.interaction_runtime import Target
from pet.companion.interaction_service import InteractionService

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
with tempfile.TemporaryDirectory(prefix='pet-companion-local-smoke-') as directory:
    cfg = Config(base=Path(directory))
    settings = cfg.chat_settings()
    settings.enabled = False  # Real local fallback, no key lookup or Provider call.
    cfg.set_chat_settings(settings)
    cfg.set('dialogue_mode', 'whale_maid')
    cfg.set('companion_interaction', {'head_touch_enabled': True, 'feeding_enabled': True})
    cfg.set('file_interpret', {'enabled': False})
    for key in ('self_talk_enabled', 'click_sound_enabled', 'self_talk_speak_enabled', 'todo_reminder_enabled'):
        cfg.set(key, False)
    cfg.set('no_move', True)
    cfg.save()
    shell = AppShell(app, cfg)
    shell.start()
    overlay = shell._overlay_shell
    host = overlay if overlay is not None else shell.win
    target = Target(host, overlay.sprite) if overlay is not None else Target(host)
    bubble = host._speech_bubble
    service = shell.companion_interactions = InteractionService()
    shown, success, errors = [], [], []
    service.delivered.connect(lambda kind, text: shown.append((kind, text)))
    stage = [0]
    deadline = time.monotonic()+45
    timer = QTimer()
    timer.setInterval(20)
    path = Path(directory)/'synthetic.png'
    path.write_bytes(b'synthetic metadata-only input')
    def tick():
        if time.monotonic() > deadline:
            print('FAIL: local real-application smoke deadline', flush=True)
            app.quit()
            return
        if stage[0] == 0 and target.valid():
            stage[0] = 1
            assert service.request('head', target)
        elif stage[0] == 1 and len(shown) == 1 and not service.busy:
            assert bubble.isVisible() and '主人' in bubble._raw_text
            # Original public drop flow, real metadata worker, stats and bubble.
            from PySide6.QtCore import QMimeData, QUrl, Qt
            from PySide6.QtGui import QDropEvent
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(path))])
            rect = overlay.sprite.rect() if overlay is not None else host._frame_draw_rect()
            point = QPointF(rect.x()+rect.width()*305/640, rect.y()+rect.height()*110/360)
            if overlay is not None:
                point = next((QPointF(rect.x()+rect.width()*x/10, rect.y()+rect.height()*y/10)
                    for y in range(1, 10) for x in range(1, 10)
                    if overlay.overlay.sprite_at(QPointF(rect.x()+rect.width()*x/10, rect.y()+rect.height()*y/10)) is overlay.sprite), None)
                if point is None:
                    return  # Wait for an opaque decoded frame, never guess a click point.
            event = QDropEvent(point, Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            overlay.overlay.dropEvent(event) if overlay is not None else host.install_file_eater().eventFilter(host, event)
            assert event.isAccepted()
            stage[0] = 2
        elif stage[0] == 2 and len(shown) == 2 and not service.busy:
            assert bubble.isVisible() and '主人' in bubble._raw_text and '读不了' not in bubble._raw_text
            assert path.read_bytes() == b'synthetic metadata-only input'
            assert (cfg.dir/'file_eaten_stats.json').is_file()
            assert not service.fake and shell.voice_chime_service is None
            assert not list(cfg.dir.glob('*sessions*')) and not list(cfg.dir.glob('*memory*'))
            print('PASS: real AppShell/assets, local maid head + original drop/stat/fun bubble, no Provider request, no TTS', flush=True)
            success.append(True)
            timer.stop()
            app.quit()
    def guarded_tick():
        try:
            tick()
        except Exception as exc:
            errors.append(repr(exc))
            print('FAIL:', errors[-1], flush=True)
            timer.stop()
            app.quit()
    timer.timeout.connect(guarded_tick)
    timer.start()
    app.exec()
    assert success == [True] and not errors, errors
