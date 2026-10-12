import json
import sqlite3
from pet.config import Config
from pet.companion.memory_store import MemoryStore
from pet.companion.proactive_state import ProactiveState
from pet.todo_reminder import TodoStore, new_todo_item
from tests.test_companion_proactive_state import START, CFG


def test_chat_variant_migrates_local_memory_quota_and_existing_todos(tmp_path, monkeypatch):
    import pet.config as config_mod
    source = Config(base=tmp_path)
    source.save()
    memory = MemoryStore(source.dir/'companion_memory.sqlite3')
    memory.put('color', '我喜欢蓝色', 'preference')
    state = ProactiveState(source.dir/'companion_proactive.sqlite3')
    token = state.reserve('old', 'care', START, CFG, 'fake')
    state.mark_presenting(token, START)
    state.finish(token, '合成测试', [], START, True)
    TodoStore(source.dir/'todo_items.json').save([new_todo_item('合成任务', 'daily', '09:00')])
    (source.dir/'file_eaten_stats.json').write_text(json.dumps({'feed_count': 7}))
    monkeypatch.setattr(config_mod, 'APP_DIR_NAME', 'dsh-pet-standalone-webm-chat')
    target = Config(base=tmp_path)
    assert MemoryStore(target.dir/'companion_memory.sqlite3').list()[0].content == '我喜欢蓝色'
    assert ProactiveState(target.dir/'companion_proactive.sqlite3').stats(START.date().isoformat())['successes'] == 1
    assert TodoStore(target.dir/'todo_items.json').load()[0]['title'] == '合成任务'
    assert json.loads((target.dir/'file_eaten_stats.json').read_text())['feed_count'] == 7
    assert memory.list()[0].content == '我喜欢蓝色'  # Source remains a rollback copy.


def test_migration_never_overwrites_existing_destination(tmp_path):
    from pet.companion.data_migration import migrate_data
    source, target = tmp_path/'source', tmp_path/'target'
    source.mkdir()
    target.mkdir()
    (source/'todo_items.json').write_text('source')
    (target/'todo_items.json').write_text('existing target')
    assert migrate_data(source, target)
    assert (target/'todo_items.json').read_text() == 'existing target'
    assert (source/'todo_items.json').read_text() == 'source'


def test_corrupt_database_is_preserved_and_migration_can_retry(tmp_path):
    from pet.companion.data_migration import migrate_data
    source, target = tmp_path/'source', tmp_path/'target'
    source.mkdir()
    broken = source/'companion_memory.sqlite3'
    broken.write_bytes(b'corrupt-original')
    assert not migrate_data(source, target)
    assert broken.read_bytes() == b'corrupt-original'
    assert not (target/'companion_memory.sqlite3').exists()
    assert not list(target.glob('*.tmp'))


def test_backup_includes_committed_wal_transactions(tmp_path):
    from pet.companion.data_migration import migrate_data
    source, target = tmp_path/'source', tmp_path/'target'
    source.mkdir()
    conn = sqlite3.connect(source/'companion_memory.sqlite3')
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('CREATE TABLE synthetic(value TEXT)')
        conn.execute("INSERT INTO synthetic VALUES ('committed-in-wal')")
        conn.commit()
        assert (source/'companion_memory.sqlite3-wal').exists()
        assert migrate_data(source, target)
        with sqlite3.connect(target/'companion_memory.sqlite3') as copy:
            assert copy.execute('SELECT value FROM synthetic').fetchone()[0] == 'committed-in-wal'
    finally:
        conn.close()


def test_failed_quota_migration_pauses_proactive_and_retries_without_overwrite(tmp_path, monkeypatch):
    import pet.config as config_mod
    from pet.companion.data_migration import PENDING
    source = Config(base=tmp_path)
    source.set('proactive_chat', {'enabled': True})
    source.save()
    broken = source.dir/'companion_proactive.sqlite3'
    broken.write_bytes(b'corrupt-original')
    monkeypatch.setattr(config_mod, 'APP_DIR_NAME', 'dsh-pet-standalone-webm-chat')
    target = Config(base=tmp_path)
    assert (target.dir/PENDING).exists()
    assert not target.get('proactive_chat')['enabled']
    # The user may safely edit the destination while the old database is repaired.
    target.set('no_move', True)
    target.save()
    broken.unlink()
    state = ProactiveState(broken)
    assert state.stats(START.date().isoformat())['successes'] == 0
    recovered = Config(base=tmp_path)
    assert not (target.dir/PENDING).exists()
    assert recovered.get('no_move') is True
    assert not recovered.get('proactive_chat')['enabled']
