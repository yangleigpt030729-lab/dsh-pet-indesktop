"""Real Qt drop/consent/follower regressions; only the provider boundary is synthetic."""
from contextlib import contextmanager
from types import SimpleNamespace
import json
import pytest
from PySide6.QtCore import QPointF
from pet.app import AppShell, PetInstance
from pet.config import Config
from pet.companion.interaction_runtime import Target
from pet.companion.interaction_service import InteractionService
from tests.test_companion_touch import window
from tests.test_companion_settings_entry import overlay_for
from tests.test_companion_chat import wait
from tests.test_companion_proactive_service import FakeProvider
from tests.test_sprite_feeding import _drop_event
from tests.test_companion_acceptance_launcher import installed_fake as _launcher_fake_fixture


@contextmanager
def hosted(tmp_path, topology, child=False):
    app, cfg, legacy = window(tmp_path/'data')
    cfg.set('click_show_self_talk', False)
    cfg.set('companion_interaction', {'head_touch_enabled': True, 'feeding_enabled': True})
    cfg.save()
    shell = AppShell(app, cfg)
    if topology == 'legacy':
        host = legacy
        if child:
            child_cfg = Config(base=cfg.dir.parent, instance_id='slot-1')
            child_cfg.set('companion_interaction', cfg.get('companion_interaction'))
            child_cfg.save()
            host.cfg = child_cfg
            instance = PetInstance(shell, child_cfg, slot_id=1)
            shell._instances.append(instance)
        else:
            instance = shell.instance
        instance.win = host
        host.companion_shell = shell
        host.on_self_talk_speak = instance._slot_wrap(shell.speak_self_talk)
        ctrl = host.install_file_interpreter()
        worker = host.install_file_eater()
        target = Target(host)
        bubble = host._speech_bubble
        drop = lambda paths: worker.eventFilter(host, _drop_event(QPointF(200, 100), paths))
    else:
        legacy.close()
        host = overlay_for(shell, cfg)
        shell._overlay_shell = host
        host.on_self_talk_speak = shell.speak_self_talk
        host.overlay.show()
        if child:
            host.spawn_pet()
            sprite = host._spawned[0]
            sprite.bind_clip('idle1')
            sprite._rebuild_pixmap()
        else:
            sprite = host.sprite
        from pet.file_interpret import FileInterpretController
        ctrl = FileInterpretController(host)
        host.set_file_interpret_offer(ctrl.offer)
        worker = host._feeding
        target = Target(host, sprite)
        bubble = host._bubble_for(sprite).bubble
        drop = lambda paths: host.overlay.dropEvent(_drop_event(QPointF(sprite.rect().center()), paths))
    state = SimpleNamespace(app=app, shell=shell, cfg=cfg, host=host, ctrl=ctrl,
                            worker=worker, target=target, bubble=bubble, drop=drop)
    try:
        yield state
    finally:
        if getattr(shell, 'companion_interactions', None):
            shell.companion_interactions.close()
        if shell.voice_chime_service:
            shell.voice_chime_service.stop()
        if topology == 'overlay':
            host.clear_spawned_pets()
            host.stop()
            host.overlay.close()
        else:
            host.close()
        shell._teardown_config_watcher()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
@pytest.mark.parametrize('failure', [False, True])
def test_real_drop_binary_directory_stats_then_safe_fun_reply(tmp_path, topology, child, failure):
    with hosted(tmp_path, topology, child) as h:
        provider = FakeProvider([RuntimeError('offline') if failure else '数字零食收到啦，原文件保持原样。'])
        service = h.shell.companion_interactions = InteractionService(provider=provider)
        paths = [tmp_path/'PRIVATE.png', tmp_path/'PRIVATE.zip', tmp_path/'PRIVATE-folder']
        paths[0].write_bytes(b'PRIVATE-BYTES')
        paths[1].write_bytes(b'PRIVATE-ZIP')
        paths[2].mkdir()
        (paths[2]/'PRIVATE.txt').write_text('PRIVATE-CONTENT', encoding='utf-8')
        before = h.bubble.text_presentation_id
        h.drop(list(map(str, paths)))
        wait(h.app, lambda: not h.worker.feed_busy)
        assert h.ctrl._state == 'idle' and h.ctrl._service is None
        assert '读不了' not in h.bubble._raw_text
        assert h.bubble.text_presentation_id > before and '吃掉' in h.bubble._raw_text
        stats = json.loads(h.worker.stats_path.read_text())
        assert stats['feed_count'] == 1 and stats['folder_count'] == 1 and stats['file_count'] >= 2
        stats_receipt = h.bubble.text_presentation_id
        wait(h.app, lambda: bool(provider.calls) and not service.busy)
        assert h.bubble.text_presentation_id > stats_receipt
        assert h.bubble.isVisible() and '读不了' not in h.bubble._raw_text
        payload = json.dumps(provider.calls[0][0], ensure_ascii=False)
        assert all(s not in payload for s in ('PRIVATE', str(tmp_path), '.png', '.zip'))
        assert paths[0].read_bytes() == b'PRIVATE-BYTES'
        assert not list(h.cfg.dir.glob('*sessions*')) and not list(h.cfg.dir.glob('*memory*'))
        assert h.shell.voice_chime_service is None
        if topology == 'overlay' and child:
            assert not h.host._speech_bubble.isVisible()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
@pytest.mark.parametrize('child', [False, True])
@pytest.mark.parametrize('decision', ['decline', 'accept', 'disabled'])
def test_real_text_drop_consent_owns_ui_and_fake_has_no_key(tmp_path, topology, child, decision, installed_fake, monkeypatch):
    from pet.chat.models import SecretStore
    import urllib.request
    def forbidden(*a, **k):
        pytest.fail('Fake read credentials or made a network request')
    monkeypatch.setattr(SecretStore, 'get', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    with hosted(tmp_path, topology, child) as h:
        if decision == 'disabled':
            if topology == 'overlay' and child:
                h.host.persist_sprite_setting(h.target.sprite_ref(), 'file_interpret', {'enabled': False})
            else:
                (h.host._config if h.target.sprite_ref else h.target.config()).set('file_interpret', {'enabled': False})
        path = tmp_path/'PRIVATE-TEXT.txt'
        path.write_text('AUTHORIZED-TEXT-CONTENT', encoding='utf-8')
        image = tmp_path/'PRIVATE-IMAGE.png'
        image.write_bytes(b'PRIVATE-IMAGE')
        h.drop([str(path), str(image)])
        wait(h.app, lambda: not h.worker.feed_busy)
        if decision != 'disabled':
            assert h.ctrl._state == 'awaiting' and h.ctrl._service is None
            assert 'PRIVATE-TEXT' in h.bubble._raw_text and 'PRIVATE-IMAGE' not in h.bubble._raw_text
            assert not h.target.valid()  # An in-flight fun/head reply cannot steal consent.
            assert not list(h.cfg.dir.glob('*sessions*'))
            if decision == 'accept':
                h.ctrl._on_confirm()
                h.ctrl._on_confirm()  # Duplicate delivery must not create a second request.
                wait(h.app, lambda: h.ctrl._state == 'idle')
                assert h.bubble.isVisible() and '解读完成' in h.bubble._raw_text
                suffix = '-'+h.target.config().instance_id if h.target.config().instance_id else ''
                assert h.ctrl._store.root == h.cfg.dir/('sessions'+suffix)
                session = h.ctrl._session
                assert len([m for m in session.messages if m.role == 'user']) == 1
                assert 'AUTHORIZED-TEXT-CONTENT' in session.messages[0].content
                assert 'PRIVATE-IMAGE' not in session.messages[0].content
                assert getattr(h.shell, 'companion_interactions', None) is None
                return
            h.ctrl._on_decline()
        service = h.shell.companion_interactions
        wait(h.app, lambda: not service.busy)
        assert '合成测试' in h.bubble._raw_text and '读不了' not in h.bubble._raw_text
        assert not list(h.cfg.dir.glob('*sessions*')) and not list(h.cfg.dir.glob('*memory*'))
        assert path.read_text(encoding='utf-8') == 'AUTHORIZED-TEXT-CONTENT'
        assert h.shell.voice_chime_service is None


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
def test_more_drops_cannot_steal_existing_consent(tmp_path, topology):
    with hosted(tmp_path, topology, child=True) as h:
        text = tmp_path/'first.txt'
        text.write_text('CONSENT-CONTENT', encoding='utf-8')
        image = tmp_path/'later.png'
        image.write_bytes(b'IMAGE')
        h.drop([str(text)])
        wait(h.app, lambda: not h.worker.feed_busy)
        assert h.ctrl._state == 'awaiting'
        receipt = h.bubble.text_presentation_id
        h.drop([str(image)])
        wait(h.app, lambda: not h.worker.feed_busy)
        assert h.bubble.text_presentation_id == receipt
        assert h.ctrl._pending == [text] and h.ctrl._service is None
        assert json.loads(h.worker.stats_path.read_text())['feed_count'] == 2
        if topology == 'overlay':
            h.host.exit_pet(h.target.sprite_ref())
            h.ctrl._on_confirm()
            assert h.ctrl._service is None and h.ctrl._state == 'idle'
        else:
            h.ctrl._on_decline()
            wait(h.app, lambda: not h.shell.companion_interactions.busy)


def test_one_overlay_interpreter_switches_child_and_primary_session_identity(tmp_path, installed_fake):
    with hosted(tmp_path, 'overlay', child=True) as h:
        path = tmp_path/'one.txt'
        path.write_text('SYNTHETIC-EXPLICIT-CONTENT', encoding='utf-8')
        h.drop([str(path)])
        wait(h.app, lambda: not h.worker.feed_busy)
        h.ctrl._on_confirm()
        wait(h.app, lambda: h.ctrl._state == 'idle')
        child_root = h.ctrl._store.root
        h.target.sprite_ref().set_pos(h.host.sprite.pos-QPointF(600, 0))
        assert h.host.overlay.sprite_at(h.host.sprite.rect().center()) is h.host.sprite
        event = _drop_event(QPointF(h.host.sprite.rect().center()), [str(path)])
        h.host.overlay.dropEvent(event)
        wait(h.app, lambda: not h.worker.feed_busy)
        assert h.ctrl._state == 'awaiting'
        h.ctrl._on_confirm()
        wait(h.app, lambda: h.ctrl._state == 'idle')
        assert child_root != h.ctrl._store.root == h.cfg.dir/'sessions'
        assert len(h.ctrl._session.messages) == 2


@pytest.fixture
def installed_fake(monkeypatch):
    return _launcher_fake_fixture.__wrapped__(monkeypatch)
