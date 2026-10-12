import json
import threading
from datetime import datetime, timezone
from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QApplication
from pet.config import Config
from pet.companion.proactive_service import ProactiveService
from pet.companion.proactive_schedule import Snapshot
from pet.companion.memory_store import MemoryStore
from tests.test_companion_chat import wait


class FakeProvider:
    def __init__(self, replies=('云朵像一条小鱼，今天想和你一起看看天空。',), barrier=None):
        self.replies = list(replies)
        self.calls = []
        self.barrier = barrier
    def stream(self, messages, config, cancel):
        self.calls.append((messages, config, QThread.currentThread()))
        if self.barrier:
            self.barrier.wait(8)
        reply = self.replies[min(len(self.calls)-1, len(self.replies)-1)]
        if isinstance(reply, Exception):
            raise reply
        yield reply


def setup(tmp_path, provider, shown=True):
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('proactive_chat', {'enabled': True})
    cfg.save()
    bubbles = []
    service = ProactiveService(cfg, lambda: Snapshot(), lambda text: (bubbles.append(text), shown)[1], provider=provider)
    return app, cfg, service, bubbles


def test_fake_real_chat_worker_single_bubble_no_global_completion(tmp_path):
    from pet.chat.service import ChatService
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider())
    calls = []
    ChatService.register_global_finished(calls.append)
    try:
        for _ in range(8):
            s.tick()
        wait(app, lambda: not s.busy)
        assert len(s.chat.provider.calls) == len(bubbles) == 1
        assert not calls
        messages, config, thread = s.chat.provider.calls[0]
        assert thread != app.thread()
        assert config.max_tokens == 96 and config.timeout <= 20
        assert '角色' in json.dumps(messages, ensure_ascii=False)
        assert not list(tmp_path.glob('*sessions*'))
        assert s.state.stats(datetime.now().astimezone().date().isoformat())['successes'] == 1
    finally:
        ChatService.unregister_global_finished(calls.append)
        s.close()


def test_cancel_and_animation_progress_during_network(tmp_path):
    barrier = threading.Event()
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider(barrier=barrier))
    ticks = []
    timer = QTimer()
    timer.setInterval(1)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    s.tick()
    wait(app, lambda: s.chat.provider.calls and ticks)
    cfg.set('proactive_chat', {'enabled': False})
    s.apply_config()
    barrier.set()
    wait(app, lambda: not s.busy and not s.chat._workers)
    timer.stop()
    assert not bubbles
    s.close()


def test_hidden_receipt_and_empty_reply(tmp_path):
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider(), shown=False)
    s.tick()
    wait(app, lambda: not s.busy)
    assert s.state.stats(datetime.now().astimezone().date().isoformat())['successes'] == 0
    s.close()


def test_readonly_memory_never_writes_and_filters_legacy_private(tmp_path):
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider())
    settings = cfg.chat_settings()
    settings.memory_enabled = True
    cfg.set_chat_settings(settings)
    cfg.save()
    store = MemoryStore(cfg.dir / 'companion_memory.sqlite3')
    store.put('preference:color', '我喜欢蓝色', 'preference')
    revision = store.revision()
    s.scheduler.activity = 7200
    s.tick(category='care')
    wait(app, lambda: not s.busy)
    assert '我喜欢蓝色' in json.dumps(s.chat.provider.calls[0][0], ensure_ascii=False)
    assert store.revision() == revision
    assert store.list()[0].content == '我喜欢蓝色'
    s.close()


def test_disabled_memory_never_opens_private_database(tmp_path, monkeypatch):
    app, cfg, s, _ = setup(tmp_path, FakeProvider())
    def forbidden(*args, **kwargs):
        raise AssertionError('private database opened without consent')
    monkeypatch.setattr(MemoryStore, '_db', forbidden)
    s.scheduler.activity = 7200
    s.tick(category='care')
    wait(app, lambda: not s.busy)
    assert len(s.chat.provider.calls) == 1
    assert '本地长期记忆引用数据' not in json.dumps(s.chat.provider.calls[0][0], ensure_ascii=False)
    s.close()


def test_memory_deleted_during_request_discards_result(tmp_path):
    barrier = threading.Event()
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider(barrier=barrier))
    settings = cfg.chat_settings()
    settings.memory_enabled = True
    cfg.set_chat_settings(settings)
    cfg.save()
    store = MemoryStore(cfg.dir/'companion_memory.sqlite3')
    store.put('color', '我喜欢蓝色', 'preference')
    s.scheduler.activity = 7200
    s.tick(category='care')
    wait(app, lambda: s.chat.provider.calls)
    store.clear()
    barrier.set()
    wait(app, lambda: not s.busy)
    assert not bubbles and store.list() == []
    s.close()


def test_manual_chat_cancels_proactive_without_interrupting_manual(tmp_path):
    from pet.chat.service import ChatService
    from pet.chat.models import ProviderConfig
    barrier = threading.Event()
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider(barrier=barrier))
    s.tick()
    wait(app, lambda: s.chat.provider.calls)
    manual = ChatService(FakeProvider(['用户主动聊天回复']))
    results = []
    manual.finished.connect(lambda rid, text: results.append(text))
    manual.send([{'role': 'user', 'content': '普通问题'}], ProviderConfig('fake'))
    barrier.set()
    wait(app, lambda: results and not s.busy and not manual._workers)
    assert results == ['用户主动聊天回复'] and not bubbles
    s.close()


def test_role_change_invalidates_old_generation(tmp_path):
    barrier = threading.Event()
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider(barrier=barrier))
    s.tick()
    wait(app, lambda: s.chat.provider.calls)
    cfg.set('character', 'another-test-role')
    barrier.set()
    wait(app, lambda: not s.busy)
    assert not bubbles
    s.close()


def test_close_never_waits_for_uninterruptible_network(tmp_path):
    import time
    barrier = threading.Event()
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider(barrier=barrier))
    s.tick()
    wait(app, lambda: s.chat.provider.calls)
    started = time.monotonic()
    s.close()
    assert time.monotonic()-started < 1
    barrier.set()
    wait(app, lambda: not s.chat._workers)
    assert not bubbles


def test_semantic_repeat_regenerates_at_most_once(tmp_path):
    from datetime import timedelta
    text = '云朵像一条小鱼，今天想和你一起看看天空。'
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider([text, text, '不该出现的第三次请求']))
    past = datetime.now().astimezone()-timedelta(hours=3)
    t = s.state.reserve('old', 'care', past, cfg.get('proactive_chat'), 'provider')
    assert t
    s.state.mark_presenting(t, past)
    s.state.finish(t, text, ['care'], past, True)
    s.tick()
    wait(app, lambda: not s.busy)
    assert len(s.chat.provider.calls) == 2 and not bubbles
    s.close()


def test_timeout_cancels_and_does_not_show_late_response(tmp_path):
    barrier = threading.Event()
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider(barrier=barrier))
    s.tick()
    wait(app, lambda: s.chat.provider.calls)
    s._timeout()  # same slot as the real 25-second deadline, no timed sleep
    barrier.set()
    wait(app, lambda: not s.busy)
    assert not bubbles
    assert len(s.chat.provider.calls) == 1
    s.close()


def test_no_credentials_uses_no_network_and_no_attempt_budget(tmp_path, monkeypatch):
    from pet.chat.models import SecretStore
    from pet.chat.providers import OpenAICompatibleProvider
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    cfg.set('proactive_chat', {'enabled': True})
    cfg.save()
    def forbidden(*a, **k):
        raise AssertionError('unexpected network')
    monkeypatch.setattr(SecretStore, 'get', lambda *a: '')
    monkeypatch.setattr(OpenAICompatibleProvider, 'stream', forbidden)
    s = ProactiveService(cfg, lambda: Snapshot(), lambda _: True)
    s.tick()
    wait(app, lambda: not s.busy)
    for _ in range(8):
        s.tick()
    assert not s.busy and '凭据' in s.status
    assert not s.state.path.exists()
    s.close()


def test_legacy_private_memory_filtered_and_double_consent(tmp_path):
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider())
    settings = cfg.chat_settings()
    settings.memory_enabled = True
    cfg.set_chat_settings(settings)
    cfg.save()
    store = MemoryStore(cfg.dir/'companion_memory.sqlite3')
    store.put('safe', '我喜欢蓝色', 'preference')
    with store._db(True) as db:
        db.execute("UPDATE memories SET content='我的邮箱是synthetic@example.invalid' WHERE topic='safe'")
    s.scheduler.activity = 7200
    s.tick(category='care')
    wait(app, lambda: not s.busy)
    assert 'synthetic@example.invalid' not in json.dumps(s.chat.provider.calls[0][0])
    s.close()


def test_memory_use_false_preserves_revision_and_sends_no_records(tmp_path):
    app, cfg, s, _ = setup(tmp_path, FakeProvider())
    settings = cfg.chat_settings()
    settings.memory_enabled = True
    cfg.set_chat_settings(settings)
    cfg.set('proactive_chat', {'enabled': True, 'use_memory': False})
    cfg.save()
    store = MemoryStore(cfg.dir/'companion_memory.sqlite3')
    store.put('safe', '我喜欢蓝色', 'preference')
    before = store.revision()
    s.scheduler.activity = 7200
    s.tick(category='care')
    wait(app, lambda: not s.busy)
    assert '我喜欢蓝色' not in json.dumps(s.chat.provider.calls[0][0], ensure_ascii=False)
    assert store.revision() == before
    s.close()


def test_database_failure_and_every_snapshot_gate_make_zero_calls(tmp_path):
    from dataclasses import replace
    app, cfg, s, _ = setup(tmp_path, FakeProvider())
    for key in ['typing', 'manual_busy', 'fullscreen', 'suspended', 'paused', 'important', 'quitting']:
        s.snapshot = lambda key=key: replace(Snapshot(), **{key: True})
        s.tick()
        assert not s.busy
    s.snapshot = lambda: Snapshot(visible=False)
    s.tick()
    assert not s.busy
    s.snapshot = lambda: Snapshot()
    s.state.path.write_bytes(b'broken database')
    s.tick()
    wait(app, lambda: not s.busy)
    assert not s.chat.provider.calls
    assert s.state.path.read_bytes() == b'broken database'
    s.close()


def test_activity_keeps_accumulating_during_global_interval(tmp_path):
    from datetime import timedelta
    app, cfg, s, _ = setup(tmp_path, FakeProvider())
    now = datetime.now().astimezone()
    s.last_mono = 10000
    s.monotonic = lambda: 10000
    s.clock = lambda: now
    s.tick()
    for tick in range(1, 60):
        s.monotonic = lambda tick=tick: 10000+tick*30
        s.clock = lambda tick=tick: now+timedelta(seconds=tick*30)
        s.tick()
    assert s.scheduler.activity == 59*30
    assert not s.chat.provider.calls
    s.close()
