import json
import threading
import time
import pytest
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication
from pet.chat.models import ProviderConfig
from pet.chat.service import ChatService
from pet.companion.memory_context import MemoryContext
from pet.companion.memory_store import MemoryStore


def wait(app, predicate):
    deadline = time.monotonic() + 10
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        threading.Event().wait(.001)
    assert predicate()


class Provider:
    def __init__(self):
        self.requests = []
        self.threads = []
    def stream(self, messages, config, cancel):
        self.requests.append(messages)
        self.threads.append(QThread.currentThread())
        yield '好的'


def send(app, context, provider=None):
    provider = provider or Provider()
    service = ChatService(provider)
    results, errors = [], []
    service.finished.connect(lambda rid, text: results.append(text))
    service.error.connect(lambda rid, text: errors.append(text))
    service.send([{'role': 'system', 'content': 'pet'}, {'role': 'user', 'content': context.user_text}], ProviderConfig('test'), memory_context=context)
    wait(app, lambda: results or errors)
    assert results == ['好的'] and not errors
    wait(app, lambda: not service._workers)
    return provider


def test_async_chat_records_on_completion_and_recalls_after_new_service(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / 'memory.db'
    provider = send(app, MemoryContext(path, '请记住我喜欢蓝色', True))
    assert provider.threads[0] != app.thread()
    assert MemoryStore(path).list()[0].content == '我喜欢蓝色'
    provider2 = send(app, MemoryContext(path, '我喜欢什么颜色', True))
    assert '我喜欢蓝色' in json.dumps(provider2.requests[0], ensure_ascii=False)
    MemoryStore(path).clear()
    provider3 = send(app, MemoryContext(path, '我喜欢什么颜色', True))
    assert '我喜欢蓝色' not in json.dumps(provider3.requests[0], ensure_ascii=False)


def test_disabled_never_opens_database(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    def forbidden(*args, **kwargs):
        raise AssertionError('private DB accessed')
    monkeypatch.setattr(MemoryStore, '_db', forbidden)
    path = tmp_path / 'never.db'
    provider = send(app, MemoryContext(path, '请记住我喜欢蓝色', False))
    assert len(provider.requests[0]) == 2 and not path.exists()


def test_corrupt_database_degrades_to_existing_chat(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / 'broken.db'
    path.write_bytes(b'broken')
    provider = send(app, MemoryContext(path, '请记住我喜欢蓝色', True))
    assert len(provider.requests[0]) == 2
    assert path.read_bytes() == b'broken'


@pytest.mark.parametrize('operation', ['delete', 'disable', 'cancel'])
def test_inflight_reply_cannot_restore_deleted_or_disabled_memory(tmp_path, operation):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / 'memory.db'
    store = MemoryStore(path)
    store.put('preference:color', '我喜欢蓝色', 'preference', 'explicit')
    policy = tmp_path / 'config.json'
    policy.write_text(json.dumps({'chat': {'memory_enabled': True}}))
    started, release = threading.Event(), threading.Event()
    class Blocked:
        def stream(self, messages, config, cancel):
            started.set()
            assert release.wait(10)
            yield 'reply'
    service = ChatService(Blocked())
    context = MemoryContext(path, '请记住我喜欢蓝色', True, policy_path=policy)
    service.send([{'role': 'user', 'content': context.user_text}], ProviderConfig('test'), memory_context=context)
    assert started.wait(5)
    if operation == 'disable':
        policy.write_text(json.dumps({'chat': {'memory_enabled': False}}))
        store.clear()
    elif operation == 'delete':
        store.clear()
    else:
        service.stop()
        store.clear()
    release.set()
    wait(app, lambda: not service._workers)
    assert store.list() == []


def test_model_reply_never_becomes_user_fact(tmp_path):
    app = QApplication.instance() or QApplication([])
    class Guesser:
        def stream(self, messages, config, cancel):
            yield '我猜你喜欢蓝色'
    path = tmp_path / 'm.db'
    service = ChatService(Guesser())
    done = []
    service.finished.connect(lambda *_: done.append(True))
    service.send([{'role': 'user', 'content': '你好'}], ProviderConfig('test'), memory_context=MemoryContext(path, '你好', True, True))
    wait(app, lambda: done)
    wait(app, lambda: not service._workers)
    assert MemoryStore(path).list() == []


@pytest.mark.parametrize('style', ['modern', 'classic'])
def test_real_chat_window_new_session_uses_memory(tmp_path, style):
    app = QApplication.instance() or QApplication([])
    from pet.config import Config
    if style == 'modern':
        from pet.chat.widgets import ChatWindow
    else:
        from pet.chat.legacy_widgets import ChatWindow
    cfg = Config(base=tmp_path)
    settings = cfg.chat_settings()
    settings.memory_enabled = True
    cfg.set_chat_settings(settings)
    cfg.save()
    window = ChatWindow(cfg, 'shenshen')
    provider = Provider()
    window.service.provider = provider
    window.input.setPlainText('请记住我喜欢蓝色')
    window.send_message()
    wait(app, lambda: len(provider.requests) == 1 and not window.service._workers)
    assert MemoryStore(cfg.dir / 'companion_memory.sqlite3').list()[0].content == '我喜欢蓝色'
    # A fresh front-end/session/provider exercises the real upstream wiring.
    second = ChatWindow(cfg, 'shenshen')
    second.new_session()
    p2 = Provider()
    second.service.provider = p2
    second.input.setPlainText('我喜欢什么颜色')
    second.send_message()
    wait(app, lambda: len(p2.requests) == 1 and not second.service._workers)
    assert '我喜欢蓝色' in json.dumps(p2.requests[0], ensure_ascii=False)
    window.close()
    second.close()


def test_attachment_content_is_never_auto_user_memory(tmp_path):
    app = QApplication.instance() or QApplication([])
    from pet.config import Config
    from pet.chat.widgets import ChatWindow
    cfg = Config(base=tmp_path)
    settings = cfg.chat_settings()
    settings.memory_enabled = settings.memory_auto_extract = True
    cfg.set_chat_settings(settings)
    cfg.save()
    attachment = tmp_path / 'someone.txt'
    attachment.write_text('我喜欢蓝色。', encoding='utf-8')
    window = ChatWindow(cfg, 'shenshen')
    provider = Provider()
    window.service.provider = provider
    window.composer.attachment_paths = [attachment]
    window.input.setPlainText('请总结这个文件')
    window.send_message()
    wait(app, lambda: provider.requests and not window.service._workers)
    assert MemoryStore(cfg.dir / 'companion_memory.sqlite3').list() == []
    window.close()


def test_policy_disable_even_when_disk_save_fails_prevents_inflight_write(tmp_path):
    app = QApplication.instance() or QApplication([])
    from pet.config import Config
    from pet.chat.ai_settings_page import _AiSettingsPage
    cfg = Config(base=tmp_path)
    settings = cfg.chat_settings()
    settings.memory_enabled = True
    cfg.set_chat_settings(settings)
    cfg.save()
    context = MemoryContext.from_config(cfg, '请记住我喜欢蓝色')
    _, token = context.prepare([{'role': 'user', 'content': context.user_text}])
    page = _AiSettingsPage(cfg)
    cfg.save = lambda: False
    page.memory_enabled.setChecked(False)
    context.completed(token)
    assert MemoryStore(context.path).list() == []


def test_busy_database_does_not_block_qt_or_break_chat(tmp_path):
    import sqlite3
    from PySide6.QtCore import QTimer
    app = QApplication.instance() or QApplication([])
    path = tmp_path / 'm.db'
    MemoryStore(path).list()
    connection = sqlite3.connect(path)
    connection.execute('BEGIN EXCLUSIVE')
    release = threading.Event()
    class ControlledProvider:
        def stream(self, messages, config, cancel):
            assert release.wait(10)
            yield '好的'
    service = ChatService(ControlledProvider())
    done, pulse = [], []
    service.finished.connect(lambda *_: done.append(True))
    service.send([{'role': 'user', 'content': '颜色'}], ProviderConfig('test'), memory_context=MemoryContext(path, '颜色', True))
    QTimer.singleShot(0, lambda: pulse.append(True))
    try:
        wait(app, lambda: pulse)
        assert not done
        release.set()
        wait(app, lambda: done and not service._workers)
    finally:
        release.set()
        service.shutdown()
        connection.rollback()
        connection.close()


def test_automatic_toggle_and_negation_update_are_persistent(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / 'm.db'
    send(app, MemoryContext(path, '我喜欢蓝色', True, False))
    assert MemoryStore(path).list() == []
    send(app, MemoryContext(path, '我喜欢蓝色', True, True))
    send(app, MemoryContext(path, '我不再喜欢蓝色', True, True))
    assert [row.content for row in MemoryStore(path).list()] == ['我不再喜欢蓝色']


def test_empty_authorized_memory_tells_model_not_to_invent_facts(tmp_path):
    app = QApplication.instance() or QApplication([])
    provider = send(app, MemoryContext(tmp_path / 'm.db', '我喜欢什么颜色', True))
    context = json.dumps(provider.requests[0], ensure_ascii=False)
    assert '不得推测用户事实' in context
    assert '[]' in context
