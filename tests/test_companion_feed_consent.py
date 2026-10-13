import pytest
from pathlib import Path
from pet.file_interpret import FileInterpretController
from tests.test_file_interpret import _qapp, _FakeWin, FakeChatService, _confirm_button, _decline_button


@pytest.mark.parametrize('kind', ['png', 'zip', 'folder'])
def test_nontext_feed_is_not_an_interpretation_error(tmp_path, kind):
    _qapp()
    win = _FakeWin(tmp_path)
    path = tmp_path/('private.'+kind)
    path.mkdir() if kind == 'folder' else path.write_bytes(b'PRIVATE-CONTENT')
    controller = FileInterpretController(win)
    assert controller.offer([path]) is False
    assert win.bubbles == [] and win.alerts == []


def test_text_consent_owns_presentation_and_decline_resumes_metadata_only(tmp_path, monkeypatch):
    _qapp()
    win = _FakeWin(tmp_path)
    service = FakeChatService()
    controller = FileInterpretController(win, service_factory=lambda: service)
    path = tmp_path/'private.txt'
    path.write_text('PRIVATE-CONTENT')
    resumed = []
    def forbidden(*args, **kwargs):
        pytest.fail('Content read before confirmation')
    monkeypatch.setattr(Path, 'open', forbidden)
    assert controller.offer([path, tmp_path/'missing.png'], on_decline=lambda: resumed.append('safe-metadata'))
    assert service.sent == [] and not win.bubbles
    _decline_button(win)()
    assert resumed == ['safe-metadata'] and service.sent == []


def test_confirmation_retains_existing_explicit_content_pipeline(tmp_path):
    _qapp()
    win = _FakeWin(tmp_path)
    service = FakeChatService()
    controller = FileInterpretController(win, service_factory=lambda: service)
    path = tmp_path/'private.txt'
    path.write_text('EXPLICIT-CONSENT-CONTENT')
    resumed = []
    assert controller.offer([path], on_decline=lambda: resumed.append(True))
    assert service.sent == []
    _confirm_button(win)()
    assert len(service.sent) == 1 and 'EXPLICIT-CONSENT-CONTENT' in str(service.sent)
    assert resumed == []


def test_optout_and_stale_confirm_cannot_read_or_submit(tmp_path, monkeypatch):
    _qapp()
    win = _FakeWin(tmp_path)
    service = FakeChatService()
    ctrl = FileInterpretController(win, service_factory=lambda: service)
    a, b = tmp_path/'old.txt', tmp_path/'new.txt'
    a.write_text('OLD', encoding='utf-8')
    b.write_text('NEW', encoding='utf-8')
    assert ctrl.offer([a])
    stale = _confirm_button(win)
    assert ctrl.offer([b])
    stale()
    assert service.sent == [] and ctrl._pending == [b]
    win._data['file_interpret'] = {'enabled': False}
    def forbidden(*a, **k):
        pytest.fail('Revoked interpretation read content')
    monkeypatch.setattr(Path, 'open', forbidden)
    _confirm_button(win)()
    assert ctrl._state == 'idle' and service.sent == []


def test_decline_callback_is_consumed_once(tmp_path):
    _qapp()
    win = _FakeWin(tmp_path)
    path = tmp_path/'one.txt'
    path.touch()
    ctrl = FileInterpretController(win)
    calls = []
    assert ctrl.offer([path], on_decline=lambda: calls.append(True))
    callback = _decline_button(win)
    callback()
    callback()
    assert calls == [True]
