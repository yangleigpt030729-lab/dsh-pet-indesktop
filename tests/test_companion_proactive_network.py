import io
import json
import threading
import urllib.error
from datetime import datetime
from PySide6.QtWidgets import QApplication
from pet.config import Config
from pet.chat.providers import OpenAICompatibleProvider
from pet.companion.proactive_service import ProactiveService
from pet.companion.proactive_schedule import Snapshot
from tests.test_companion_chat import wait


def test_real_provider_mock_sse_payload_and_thread_boundary(tmp_path, monkeypatch):
    from PySide6.QtCore import QThread
    from pet.chat import providers
    from pet.companion.proactive_state import ProactiveState
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('proactive_chat', {'enabled': True})
    settings = cfg.chat_settings()
    settings.default_system_prompt = '测试角色：温柔的大肥鱼。'
    settings.active_config.api_key = 'FAKE-TEST-ONLY-NOT-A-REAL-KEY'
    cfg.set_chat_settings(settings)
    cfg.set('character', 'synthetic-role')
    cfg.save()
    threads, requests = [], []
    def urlopen(request, **kwargs):
        threads.append(QThread.currentThread())
        requests.append(json.loads(request.data))
        assert kwargs['timeout'] <= 20
        return io.BytesIO(b'data: '+json.dumps({'choices': [{'delta': {'content': '今天也慢慢来，本鱼就在这里陪你。'}}]}, ensure_ascii=False).encode()+b'\n\ndata: [DONE]\n\n')
    monkeypatch.setattr(providers.urllib.request, 'urlopen', urlopen)
    original = ProactiveState.db
    def record_db(self):
        threads.append(QThread.currentThread())
        return original(self)
    monkeypatch.setattr(ProactiveState, 'db', record_db)
    bubbles = []
    s = ProactiveService(cfg, lambda: Snapshot(), lambda t: (bubbles.append(t), True)[1])
    s.tick()
    wait(app, lambda: not s.busy)
    assert len(requests) == len(bubbles) == 1
    assert requests[0]['max_tokens'] == 96
    assert requests[0]['messages'][0]['content'] == settings.default_system_prompt
    assert all(t != app.thread() for t in threads)
    assert b'FAKE-TEST-ONLY-NOT-A-REAL-KEY' not in s.state.path.read_bytes()
    assert all(m['role'] == 'system' for m in requests[0]['messages'])
    s.close()


def test_real_provider_http429_retry_after_mock(tmp_path, monkeypatch):
    from pet.chat import providers
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('proactive_chat', {'enabled': True})
    settings = cfg.chat_settings()
    settings.active_config.api_key = 'FAKE-TEST-ONLY-NOT-A-REAL-KEY'
    cfg.set_chat_settings(settings)
    cfg.save()
    calls = []
    def urlopen(request, **kwargs):
        calls.append(request)
        raise urllib.error.HTTPError(request.full_url, 429, 'limited', {'Retry-After': '3600'}, io.BytesIO(b'private response'))
    monkeypatch.setattr(providers.urllib.request, 'urlopen', urlopen)
    s = ProactiveService(cfg, lambda: Snapshot(), lambda _: True)
    s.tick()
    wait(app, lambda: not s.busy)
    s.tick()
    wait(app, lambda: not s.busy)
    assert len(calls) == 1
    assert s.state.stats(datetime.now().astimezone().date().isoformat())['successes'] == 0
    assert 'private response' not in s.status
    s.close()


def test_cancel_response_close_cannot_block_gui(tmp_path, monkeypatch):
    from pet.chat import providers
    app = QApplication.instance() or QApplication([])
    read_started, close_started, release = threading.Event(), threading.Event(), threading.Event()
    class Response:
        def read(self, _):
            read_started.set()
            release.wait(10)
            return b''
        def close(self):
            close_started.set()
            release.wait(10)
    monkeypatch.setattr(providers.urllib.request, 'urlopen', lambda *a, **k: Response())
    cfg = Config(base=tmp_path)
    cfg.set('proactive_chat', {'enabled': True})
    cfg.save()
    # Explicit injection is the test-only keyless seam; still exercises real provider.
    s = ProactiveService(cfg, lambda: Snapshot(), lambda _: True, provider=OpenAICompatibleProvider())
    s.tick()
    wait(app, read_started.is_set)
    s.cancel()
    assert close_started.wait(3)
    assert not release.is_set()  # cancel returned while response.close remains blocked
    release.set()
    wait(app, lambda: not s.busy)
    s.close()
