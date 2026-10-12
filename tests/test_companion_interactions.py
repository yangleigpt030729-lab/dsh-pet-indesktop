import hashlib
import json
import threading
import pytest
from PySide6.QtWidgets import QApplication
from pet.companion.interaction_service import InteractionService
from pet.config import Config
from pet.companion.memory_store import MemoryStore
from tests.test_companion_proactive_service import FakeProvider
from tests.test_companion_chat import wait


class Target:
    def __init__(self, cfg):
        self.cfg = cfg
        self.key = str(cfg.path)
        self.texts = []
        self.alive = True
        self.manual = False
    def config(self):
        return self.cfg
    def identity(self):
        return hashlib.sha256(json.dumps(self.cfg.data, sort_keys=True).encode()).hexdigest()
    def valid(self):
        return self.alive
    def manual_busy(self):
        return self.manual
    def present(self, text):
        self.texts.append(text)
        return True


def setup(tmp_path, provider=None):
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('companion_interaction', {'head_touch_enabled': True, 'feeding_enabled': True})
    cfg.save()
    target = Target(cfg)
    service = InteractionService(provider=provider)
    return app, cfg, target, service


def test_async_touch_has_no_global_completion_session_or_proactive_quota(tmp_path, monkeypatch):
    from pet.chat.service import ChatService
    from pet.chat.models import SecretStore
    from pet import vision
    from PySide6.QtMultimedia import QCamera, QAudioSource
    def forbidden(*a, **k):
        pytest.fail('Synthetic interaction used credentials/capture/global completion')
    monkeypatch.setattr(SecretStore, 'get', forbidden)
    monkeypatch.setattr(vision, 'capture_screen_bytes', forbidden)
    monkeypatch.setattr(QCamera, 'start', forbidden)
    monkeypatch.setattr(QAudioSource, 'start', forbidden)
    ChatService.register_global_finished(forbidden)
    provider = FakeProvider(['鱼鳍开心地翘起来啦，谢谢你温柔地摸摸我。'])
    app, cfg, target, s = setup(tmp_path, provider)
    try:
        assert s.request('head', target)
        for _ in range(30):
            assert not s.request('head', target)
        wait(app, lambda: not s.busy)
        assert len(target.texts) == len(provider.calls) == 1
        assert provider.calls[0][2] != app.thread()
        assert provider.calls[0][1].max_tokens == 96
        assert not list(cfg.dir.glob('*.sqlite3')) and not list(cfg.dir.glob('*sessions*'))
    finally:
        s.close()
        ChatService.unregister_global_finished(forbidden)


@pytest.mark.parametrize('operation', ['delete', 'disable', 'close', 'manual', 'destroy'])
def test_touch_result_is_canceled_after_privacy_or_lifecycle_change(tmp_path, operation):
    barrier = threading.Event()
    provider = FakeProvider(['摸到我啦，我很开心。'], barrier=barrier)
    app, cfg, target, s = setup(tmp_path, provider)
    settings = cfg.chat_settings()
    settings.memory_enabled = True
    cfg.set_chat_settings(settings)
    cfg.save()
    store = MemoryStore(cfg.dir/'companion_memory.sqlite3')
    store.put('color', '我喜欢蓝色', 'preference')
    try:
        s.request('head', target)
        wait(app, lambda: provider.calls)
        assert '我喜欢蓝色' in json.dumps(provider.calls[0][0], ensure_ascii=False)
        if operation == 'delete':
            store.clear()
        elif operation == 'disable':
            cfg.set('companion_interaction', {'head_touch_enabled': False})
        elif operation == 'close':
            s.close()
        elif operation == 'manual':
            target.manual = True
            s.cancel()
        else:
            target.alive = False
        barrier.set()
        wait(app, lambda: not s.busy and not s.chat._workers)
        assert not target.texts
        assert len(store.list()) == (0 if operation == 'delete' else 1)
    finally:
        barrier.set()
        s.close()


def test_missing_live_key_falls_back_without_request(tmp_path, monkeypatch):
    from pet.chat.models import SecretStore
    from pet.chat.providers import OpenAICompatibleProvider
    monkeypatch.setattr(SecretStore, 'get', lambda *a: '')
    monkeypatch.setattr(OpenAICompatibleProvider, 'stream', lambda *a, **k: pytest.fail('Keyless live request'))
    app, cfg, target, s = setup(tmp_path)
    try:
        assert not s.fake
        assert s.request('head', target)
        wait(app, lambda: not s.busy)
        assert len(target.texts) == 1
    finally:
        s.close()


def test_disabled_memory_never_opens_database_and_reply_is_not_extracted(tmp_path, monkeypatch):
    provider = FakeProvider(['我喜欢蓝色。'])
    app, cfg, target, s = setup(tmp_path, provider)
    monkeypatch.setattr(MemoryStore, '_db', lambda *a, **k: pytest.fail('Private store opened'))
    try:
        s.request('head', target)
        wait(app, lambda: not s.busy)
        assert target.texts and '本地长期记忆' not in json.dumps(provider.calls[0][0], ensure_ascii=False)
        assert not (cfg.dir/'companion_memory.sqlite3').exists()
    finally:
        s.close()


def test_model_failure_repeated_clicks_have_no_paid_retry_storm(tmp_path):
    provider = FakeProvider([RuntimeError('Synthetic failure')])
    app, cfg, target, s = setup(tmp_path, provider)
    mono = [100.0]
    s.clock = lambda: mono[0]
    try:
        s.request('head', target)
        wait(app, lambda: not s.busy)
        mono[0] += 11
        assert s.request('head', target)
        wait(app, lambda: not s.busy)
        assert len(provider.calls) == 1 and len(target.texts) == 2
    finally:
        s.close()
