import pytest
from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap, QMouseEvent
from PySide6.QtWidgets import QApplication
from pet.config import Config
from pet.window import PetWindow
from tests.test_context_menu_lifecycle import FakeLibrary


@pytest.mark.parametrize('mirror', [False, True])
@pytest.mark.parametrize('scale,dpr', [(1, 1), (.5, 1), (.75, 1.25), (.55, 1.5)])
def test_core_head_survives_overlap_scale_mirror_and_offset(mirror, scale, dpr):
    from pet.companion.touch_region import head_core_at
    rect = QRect(19, 31, round(640*scale), round(360*scale))
    def point(x, y):
        return QPointF(rect.x()+(640-x if mirror else x)*rect.width()/640,
                       rect.y()+y*rect.height()/360)
    assert head_core_at('shenshen', point(305, 110), rect, mirror)
    assert not head_core_at('shenshen', point(305, 240), rect, mirror)
    assert not head_core_at('shenshen', point(220, 190), rect, mirror)
    assert not head_core_at('shenshen', point(185, 60), rect, mirror)


def window(tmp_path):
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('character', 'shenshen')
    cfg.set('companion_interaction', {'head_touch_enabled': True, 'feeding_enabled': False})
    cfg.set('click_sound_enabled', False)
    lib = FakeLibrary()
    image = QImage(640, 360, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.fillRect(QRect(185, 60, 251, 270), Qt.GlobalColor.blue)
    painter.end()
    for clip in lib.movies().values():
        clip._pm = QPixmap.fromImage(image)
    win = PetWindow(lib, cfg)
    win.show()
    win._rebuild_frame()
    return app, cfg, win


def send(win, kind, point, button=Qt.MouseButton.LeftButton):
    buttons = button if kind != QMouseEvent.Type.MouseButtonRelease else Qt.MouseButton.NoButton
    event = QMouseEvent(kind, QPointF(point), QPointF(win.mapToGlobal(point)), button, buttons, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(win, event)


@pytest.mark.parametrize('region', ['head', 'body', 'boundary', 'transparent', 'drag', 'right', 'disabled'])
def test_real_legacy_mouse_release_routes_one_primary_interaction(tmp_path, region):
    from pet.companion.interaction_runtime import legacy_head
    app, cfg, win = window(tmp_path)
    requests, ordinary = [], []
    from types import SimpleNamespace
    shell = SimpleNamespace(enable_chat=True, config=cfg, companion_interactions=SimpleNamespace(
        request=lambda *a, **k: requests.append((a, k)) or True))
    win.on_companion_head_click = lambda point, press: legacy_head(shell, win, point, press)
    win._on_click = lambda: ordinary.append(True)
    rect = win._frame_draw_rect()
    x, y = (305, 110) if region in ('head', 'drag', 'right', 'disabled') else ((305, 240) if region == 'body' else (220, 190) if region == 'boundary' else (2, 2))
    point = QPoint(rect.x()+round(x*rect.width()/640), rect.y()+round(y*rect.height()/360))
    if region == 'disabled':
        cfg.set('companion_interaction', {'head_touch_enabled': False})
    button = Qt.MouseButton.RightButton if region == 'right' else Qt.MouseButton.LeftButton
    try:
        send(win, QMouseEvent.Type.MouseButtonPress, point, button)
        if region == 'drag':
            send(win, QMouseEvent.Type.MouseMove, point+QPoint(70, 50), button)
        send(win, QMouseEvent.Type.MouseButtonRelease, point, button)
        assert len(requests) == (1 if region == 'head' else 0)
        assert len(ordinary) == (1 if region in ('body', 'boundary', 'disabled') else 0)
    finally:
        win.close()
        app.processEvents()


@pytest.mark.parametrize('region', ['head', 'body', 'boundary', 'drag', 'disabled'])
@pytest.mark.parametrize('child', [False, True])
def test_overlay_real_event_chain_and_correct_pet(tmp_path, region, child):
    from types import SimpleNamespace
    from pet.app import PetInstance
    from tests.test_settings_process_isolation import _bare_shell
    from tests.test_companion_settings_entry import overlay_for
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('companion_interaction', {'head_touch_enabled': region != 'disabled'})
    cfg.set('click_sound_enabled', False)
    cfg.save()
    shell = _bare_shell(cfg)
    shell.enable_chat = True
    shell.instance = PetInstance(shell, cfg)
    shell._instances = [shell.instance]
    requests, ordinary = [], []
    shell.companion_interactions = SimpleNamespace(request=lambda *a: requests.append(a) or True)
    host = overlay_for(shell, cfg)
    host.overlay.show()
    if child:
        host.spawn_pet()
    sprite = host._spawned[0] if child else host.sprite
    sprite.bind_clip('idle1')
    sprite._rebuild_pixmap()
    host.overlay._on_sprite_click = lambda *a: ordinary.append(a)
    rect = sprite.rect()
    x, y = (305, 110) if region in ('head', 'drag', 'disabled') else (305, 240) if region == 'body' else (220, 190)
    point = QPoint(rect.x()+round(x*rect.width()/640), rect.y()+round(y*rect.height()/360))
    try:
        send(host.overlay, QMouseEvent.Type.MouseButtonPress, point)
        if region == 'drag':
            send(host.overlay, QMouseEvent.Type.MouseMove, point+QPoint(70, 50))
        send(host.overlay, QMouseEvent.Type.MouseButtonRelease, point)
        assert len(requests) == (1 if region == 'head' else 0)
        assert len(ordinary) == (1 if region in ('body', 'boundary', 'disabled') else 0)
        if requests:
            assert requests[0][1].sprite_ref() is sprite
    finally:
        host.clear_spawned_pets()
        host.stop()
        host.overlay.close()
