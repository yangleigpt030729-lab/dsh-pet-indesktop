import json
import threading
from pathlib import Path
from PySide6.QtCore import QMimeData, QUrl, QPointF, Qt
from PySide6.QtGui import QDropEvent
from pet.companion.interaction_service import safe_metadata
from tests.test_companion_chat import wait
from tests.test_companion_interactions import setup
from tests.test_companion_proactive_service import FakeProvider


def test_file_metadata_never_includes_names_paths_or_bytes(tmp_path):
    from pet.companion.feeding_metadata import describe
    image = tmp_path/'私人名称照片.png'
    code = tmp_path/'私人项目.py'
    folder = tmp_path/'私人资料夹'
    folder.mkdir()
    (folder/'never_upload.txt').write_text('SECRET-CONTENT')
    image.write_bytes(b'PRIVATE-IMAGE-BYTES')
    code.write_text('PRIVATE-CODE-BODY')
    result = describe([image, code, folder, tmp_path/'missing'])
    data = json.dumps(result['metadata'], ensure_ascii=False)
    assert result['metadata']['categories'] == {'image': 1, 'python': 1, 'folder': 1}
    assert result['files'] == 2 and result['folders'] == 1
    for private in ('私人', str(tmp_path), 'SECRET', 'PRIVATE', '.png', '.py'):
        assert private not in data
    assert image.read_bytes() == b'PRIVATE-IMAGE-BYTES'


def test_injected_metadata_is_reduced_to_safe_allowlist():
    result = safe_metadata({'path': 'PRIVATE', 'filename': 'SECRET', 'bytes': b'abc',
                            'categories': {'python': 1, 'private_extension': 2},
                            'files': 1, 'folders': 0, 'size_bucket': 'small'})
    assert set(result) == {'categories', 'files', 'folders', 'size_bucket'}
    assert result['categories'] == {'python': 1}


def test_feed_provider_only_gets_safe_metadata_and_never_memory(tmp_path):
    provider = FakeProvider(['Python类型像一份括号点心，原文件仍在原地。'])
    app, cfg, target, s = setup(tmp_path, provider)
    settings = cfg.chat_settings()
    settings.memory_enabled = True
    cfg.set_chat_settings(settings)
    cfg.save()
    try:
        s.request('feeding', target, {'categories': {'python': 1}, 'files': 1,
                                    'filename': 'PRIVATE.py', 'path': 'D:/PRIVATE'})
        wait(app, lambda: not s.busy)
        payload = '\n'.join(m['content'] for m in provider.calls[0][0])
        assert 'PRIVATE' not in payload and '"python": 1' in payload
        assert target.texts and not list(cfg.dir.glob('*.sqlite3'))
    finally:
        s.close()


def test_feed_burst_is_merged_and_generates_one_model_request(tmp_path):
    provider = FakeProvider(['本鱼收到了这一盒数字零食，谢谢投喂。'])
    app, cfg, target, s = setup(tmp_path, provider)
    try:
        for _ in range(12):
            s.offer_feeding(target, {'categories': {'python': 1}, 'files': 1, 'size_bucket': 'tiny'})
        wait(app, lambda: len(provider.calls) == 1 and not s.busy)
        payload = '\n'.join(m['content'] for m in provider.calls[0][0])
        assert '"python": 12' in payload and '"files": 12' in payload
        assert len(target.texts) == 1
    finally:
        s.close()


def test_legacy_drop_plays_immediately_while_metadata_worker_is_blocked(tmp_path, monkeypatch):
    from tests.test_file_eater import _make_pet
    from PySide6.QtWidgets import QApplication
    from pet.file_eater import FileEaterDropHandler
    from pet.companion import feeding_metadata
    app = QApplication.instance() or QApplication([])
    pet = _make_pet(tmp_path)
    handler = FileEaterDropHandler(pet)
    path = tmp_path/'中文.py'
    path.write_text('private')
    started, release = threading.Event(), threading.Event()
    original = feeding_metadata.describe
    def blocked(*a, **k):
        started.set()
        release.wait(10)
        return original(*a, **k)
    monkeypatch.setattr(feeding_metadata, 'describe', blocked)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    event = QDropEvent(QPointF(5, 5), Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    try:
        handler.eventFilter(pet, event)
        assert event.isAccepted() and pet.anim_requests[-1] == '吃Token'
        wait(app, started.is_set)
        assert handler.feed_busy
        release.set()
        wait(app, lambda: not handler.feed_busy)
        assert (tmp_path/'file_eaten_stats.json').exists()
        assert path.read_text() == 'private'
    finally:
        release.set()
        pet.close()


def test_large_directory_metadata_is_bounded_and_marked_incomplete(tmp_path, monkeypatch):
    from pet.companion.feeding_metadata import describe
    folder = tmp_path/'large'
    folder.mkdir()
    for n in range(5):
        (folder/str(n)).write_text('abc')
    result = describe([folder], max_entries=2)
    assert result['partial'] is True
    assert result['metadata']['size_bucket'] == 'unknown'


def test_overlay_child_drop_has_real_bubble_correct_animation_and_private_payload(tmp_path):
    from PySide6.QtWidgets import QApplication
    from pet.app import PetInstance
    from pet.config import Config
    from pet.companion.interaction_service import InteractionService
    from tests.test_settings_process_isolation import _bare_shell
    from tests.test_companion_settings_entry import overlay_for
    from tests.test_sprite_feeding import _drop_event
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('companion_interaction', {'feeding_enabled': True})
    cfg.set('click_sound_enabled', False)
    cfg.save()
    shell = _bare_shell(cfg)
    shell.enable_chat = True
    shell.instance = PetInstance(shell, cfg)
    shell._instances = [shell.instance]
    provider = FakeProvider(['收到这份括号点心啦，只凭类型想象就很开心。'])
    s = shell.companion_interactions = InteractionService(provider=provider)
    host = overlay_for(shell, cfg)
    host.overlay.show()
    host.spawn_pet()
    child = host._spawned[0]
    child.bind_clip('idle1')
    child._rebuild_pixmap()
    path = tmp_path/'私人项目.py'
    path.write_text('SECRET-SOURCE-BYTES', encoding='utf-8')
    main_clip = host.sprite._clip_name
    try:
        event = _drop_event(QPointF(child.rect().center()), [str(path)])
        host.overlay.dropEvent(event)
        assert event.isAccepted()
        assert child._clip_name == 'act1' and host.sprite._clip_name == main_clip
        wait(app, lambda: bool(provider.calls) and not s.busy and not host._feeding.feed_busy)
        bubble = host._bubble_for(child).bubble
        assert bubble.isVisible() and '括号点心' in bubble._raw_text
        assert not host._speech_bubble.isVisible()
        payload = '\n'.join(m['content'] for m in provider.calls[0][0])
        assert '私人' not in payload and str(tmp_path) not in payload and 'SECRET' not in payload
        assert path.read_text(encoding='utf-8') == 'SECRET-SOURCE-BYTES'
        assert not (cfg.dir/'companion_memory.sqlite3').exists()
    finally:
        s.close()
        host.clear_spawned_pets()
        host.stop()
        host.overlay.close()
