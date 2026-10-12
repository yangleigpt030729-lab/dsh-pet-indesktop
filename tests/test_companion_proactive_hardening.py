from datetime import datetime, timedelta, timezone
import json
import pytest
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication
from pet.config import Config
from pet.window import PetWindow
from pet.companion.proactive_state import ProactiveState
from pet.companion.proactive_config import normalize_config
from tests.test_window_broker_wiring import FakeLibrary
from tests.test_companion_proactive_service import FakeProvider, setup
from tests.test_companion_chat import wait

NOW = datetime(2026, 10, 12, 23, 59, 30, tzinfo=timezone.utc)
CFG = normalize_config({'enabled': True})


@pytest.mark.parametrize('old', ['旧审批内容', '本次候选内容'])
def test_legacy_rejected_new_text_is_not_success_even_if_old_visible(tmp_path, old):
    app = QApplication.instance() or QApplication([])
    win = PetWindow(FakeLibrary(), Config(base=tmp_path))
    try:
        win.show()
        win._speech_bubble.show_text(old, QRect(0, 0, 100, 100), buttons=[('确认', lambda: None)])
        assert win._speech_bubble.isVisible()
        assert not win.try_show_bubble('本次候选内容')
        assert win._speech_bubble._raw_text == old
    finally:
        win.close()
        app.processEvents()


def seed_full_day(store, day):
    with store.db() as db:
        db.execute('INSERT OR REPLACE INTO days VALUES (?,10,10,960)', (day,))


def test_finish_cannot_transfer_old_claim_to_full_new_day(tmp_path):
    store = ProactiveState(tmp_path/'p.db')
    token = store.reserve('old', 'care', NOW, CFG, 'fake')
    assert store.mark_presenting(token, NOW)
    next_day = NOW+timedelta(minutes=1)
    seed_full_day(store, next_day.date().isoformat())
    assert not store.finish(token, '跨日候选', ['care'], next_day, True)
    assert store.stats(next_day.date().isoformat())['successes'] == 10


def test_finish_and_mark_recheck_cap_and_preserve_uncertain_claim(tmp_path):
    store = ProactiveState(tmp_path/'p.db')
    token = store.reserve('old', 'care', NOW, CFG, 'fake')
    assert store.mark_presenting(token, NOW)
    seed_full_day(store, NOW.date().isoformat())
    assert not store.finish(token, '候选', ['care'], NOW, True)
    assert store.stats(NOW.date().isoformat())['successes'] == 10
    with store.db() as db:
        assert db.execute('SELECT 1 FROM reservations WHERE id=?', (token,)).fetchone()


def test_finish_rejects_backwards_presentation_timestamp(tmp_path):
    store = ProactiveState(tmp_path/'p.db')
    token = store.reserve('old', 'care', NOW, CFG, 'fake')
    assert store.mark_presenting(token, NOW)
    assert not store.finish(token, '候选', [], NOW-timedelta(seconds=1), True)
    assert store.stats(NOW.date().isoformat())['successes'] == 0


def test_crash_across_midnight_cannot_bypass_shared_interval(tmp_path):
    path = tmp_path/'p.db'
    store = ProactiveState(path)
    token = store.reserve('old', 'care', NOW, CFG, 'fake')
    store.mark_presenting(token, NOW)
    restart = ProactiveState(path)
    assert not restart.reserve('new', 'drink', NOW+timedelta(minutes=2), CFG, 'fake')
    assert not restart.reserve('new', 'drink', NOW+timedelta(minutes=30), CFG, 'fake')
    assert restart.reserve('new', 'drink', NOW+timedelta(minutes=30, seconds=5), CFG, 'fake')


@pytest.mark.parametrize('enabled', [False, True])
def test_recent_utterance_never_reuploads_private_words(tmp_path, enabled):
    app, cfg, service, _ = setup(tmp_path, FakeProvider())
    settings = cfg.chat_settings()
    settings.memory_enabled = enabled
    cfg.set_chat_settings(settings)
    cfg.save()
    now = datetime.now().astimezone()
    earlier = now-timedelta(hours=3)
    token = service.state.reserve('old', 'care', earlier, CFG, 'fake')
    service.state.mark_presenting(token, earlier)
    service.state.finish(token, '小明，祝你的项目私密名称取得进展。', ['care', '私密名称'], earlier, True)
    service.tick()
    wait(app, lambda: not service.busy)
    payload = json.dumps(service.chat.provider.calls[0][0], ensure_ascii=False)
    assert '小明' not in payload and '私密名称' not in payload
    assert 'care' in payload
    service.close()


def test_midnight_fence_and_retry_cannot_use_yesterday_budget(tmp_path):
    store = ProactiveState(tmp_path/'p.db')
    token = store.reserve('old', 'care', NOW, CFG, 'fake')
    assert not store.retry_attempt(token, CFG, NOW+timedelta(minutes=1))
    assert store.stats(NOW.date().isoformat())['attempts'] == 1
    assert not store.mark_presenting(token, NOW+timedelta(seconds=26))
    assert not store.reserve('fence', 'care', NOW+timedelta(seconds=26), CFG, 'fake')


def test_late_settlement_uses_receipt_day_not_worker_wall_time(tmp_path):
    store = ProactiveState(tmp_path/'p.db')
    token = store.reserve('old', 'care', NOW, CFG, 'fake')
    store.mark_presenting(token, NOW)
    # It may be tomorrow when the queue drains; the authentic receipt stays immutable.
    assert store.finish(token, '昨日已经显示', [], NOW+timedelta(seconds=1), True)
    assert store.stats(NOW.date().isoformat())['successes'] == 1
    assert store.stats((NOW+timedelta(days=1)).date().isoformat())['successes'] == 0


def test_actual_processes_settle_last_slot_once(tmp_path):
    import subprocess
    import sys
    store = ProactiveState(tmp_path/'p.db')
    token = store.reserve('last', 'care', NOW, CFG, 'fake')
    store.mark_presenting(token, NOW)
    with store.db() as db:
        db.execute('UPDATE days SET successes=9')
    code = "from pet.companion.proactive_state import ProactiveState;from datetime import datetime;import sys;print('ready',flush=True);sys.stdin.readline();print(int(ProactiveState(sys.argv[1]).finish(sys.argv[2],'合成台词',[],datetime.fromisoformat(sys.argv[3]),True)),flush=True)"
    children = [subprocess.Popen([sys.executable, '-c', code, str(store.path), token, NOW.isoformat()], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) for _ in range(6)]
    from concurrent.futures import ThreadPoolExecutor
    readers = ThreadPoolExecutor(6)
    readiness = [readers.submit(child.stdout.readline) for child in children]
    try:
        for ready in readiness:
            assert ready.result(timeout=15).strip() == 'ready'
        for child in children:
            child.stdin.write('go\n')
            child.stdin.flush()
        results = [child.communicate(timeout=15)[0].strip() for child in children]
        assert results.count('1') == 1 and results.count('0') == 5
        assert all(child.returncode == 0 for child in children)
        assert store.stats(NOW.date().isoformat())['successes'] == 10
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(5)
        readers.shutdown(wait=True)


def test_v1_migration_keeps_crash_interval_across_midnight(tmp_path):
    import sqlite3
    path = tmp_path/'p.db'
    db = sqlite3.connect(path)
    db.executescript('''CREATE TABLE days(day TEXT PRIMARY KEY,successes INTEGER,attempts INTEGER,tokens INTEGER);
    CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE reservations(id TEXT PRIMARY KEY,event TEXT,day TEXT,category TEXT,status TEXT,utc REAL,expires REAL,attempts INTEGER);
    CREATE TABLE utterances(id TEXT PRIMARY KEY,event TEXT,text TEXT,tags TEXT,utc REAL,day TEXT);
    PRAGMA user_version=1;''')
    db.execute('INSERT INTO reservations VALUES (?,?,?,?,?,?,?,?)', ('old','old',NOW.date().isoformat(),'care','presenting',NOW.timestamp(),NOW.timestamp()+60,1))
    db.commit()
    db.close()
    assert not ProactiveState(path).reserve('new','drink',NOW+timedelta(minutes=2),CFG,'fake')
    with ProactiveState(path).db() as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 2


def test_worker_guard_drops_expired_request_without_provider_call(tmp_path):
    from pet.chat.service import ChatService
    from pet.chat.models import ProviderConfig
    from pet.companion.memory_context import MemoryContext
    from pet.companion.proactive_context import ReadOnlyMemory
    app = QApplication.instance() or QApplication([])
    provider = FakeProvider()
    service = ChatService(provider, notify_global=False)
    context = ReadOnlyMemory(MemoryContext(tmp_path/'m.db','',False), False,
                             window={'day': NOW.date().isoformat(), 'expires': NOW.timestamp()+10},
                             clock=lambda: NOW+timedelta(days=1))
    errors = []
    service.error.connect(lambda *args: errors.append(args))
    service.send([{'role':'system','content':'内部合成任务'}],ProviderConfig('fake'),memory_context=context)
    wait(app, lambda: errors and not service._workers)
    assert not provider.calls
    assert not (tmp_path/'m.db').exists()


@pytest.mark.parametrize('revocation', ['reading', 'use_memory', 'deletion', 'failed_save'])
def test_real_authorized_care_then_revoke_never_resends_fact(tmp_path, monkeypatch, revocation):
    from pet.companion.memory_store import MemoryStore
    from pet.companion.memory_context import MemoryContext
    app, cfg, service, _ = setup(tmp_path, FakeProvider(['合成代号海帆，希望你的项目顺利。','今天也慢慢来呀。']))
    settings = cfg.chat_settings()
    settings.memory_enabled = True
    cfg.set_chat_settings(settings)
    cfg.save()
    store = MemoryStore(cfg.dir/'companion_memory.sqlite3')
    store.put('project', '我的项目叫合成代号海帆', 'fact')
    current = datetime.now().astimezone()
    service.clock = lambda: current-timedelta(hours=3)
    service.monotonic = lambda: 10000
    service.scheduler.activity = 7200
    service.tick(category='care')
    wait(app, lambda: not service.busy)
    assert '合成代号海帆' in json.dumps(service.chat.provider.calls[0][0],ensure_ascii=False)
    assert '合成代号海帆' in service.state.recent()[0]['text']
    if revocation == 'deletion':
        store.clear()
    elif revocation == 'use_memory':
        cfg.set('proactive_chat', {'enabled':True,'use_memory':False})
        cfg.save()
    elif revocation == 'reading':
        settings.memory_enabled = False
        cfg.set_chat_settings(settings)
        cfg.save()
    else:
        MemoryContext.set_runtime_policy(cfg.path, False)  # immediate opt-out even if disk save fails
    if revocation != 'deletion':
        monkeypatch.setattr(MemoryStore, '_db', lambda *a, **k: pytest.fail('revoked memory read'))
    service.clock = lambda: current
    service.monotonic = lambda: 20800
    service.tick()
    wait(app, lambda: not service.busy)
    assert len(service.chat.provider.calls) == 2
    assert '合成代号海帆' not in json.dumps(service.chat.provider.calls[1][0],ensure_ascii=False)
    service.close()


def test_proactive_path_never_calls_tts_or_capture(tmp_path, monkeypatch):
    from pet import vision
    from pet.app import AppShell
    from pet.chat.service import ChatService
    from pet.voice_chime_service import VoiceChimeService
    def forbidden(*a, **k):
        pytest.fail('proactive TTS/capture/global completion')
    monkeypatch.setattr(vision, 'capture_screen_bytes', forbidden)
    monkeypatch.setattr(vision, 'capture_window_rect', forbidden)
    monkeypatch.setattr(AppShell, 'speak_self_talk', forbidden)
    monkeypatch.setattr(VoiceChimeService, 'speak', forbidden)
    ChatService.register_global_finished(forbidden)
    app, cfg, service, bubbles = setup(tmp_path, FakeProvider())
    try:
        service.tick()
        wait(app, lambda: not service.busy)
        assert len(bubbles) == 1
    finally:
        service.close()
        ChatService.unregister_global_finished(forbidden)
