from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import pytest
from pet.companion.proactive_config import normalize_config
from pet.companion.proactive_state import ProactiveState, StateUnavailable

CFG = normalize_config({'enabled': True})
START = datetime(2026, 10, 12, 8, tzinfo=timezone.utc)


def test_default_privacy_and_bounds():
    assert not normalize_config(None)['enabled']
    assert normalize_config({'enabled': 'true'})['enabled'] is False
    assert normalize_config({'daily_limit': 100, 'min_interval_minutes': 0})['daily_limit'] == 100
    assert normalize_config({'daily_limit': 100, 'min_interval_minutes': 0})['min_interval_minutes'] == 1


def reserve(store, n, now=START, config=CFG):
    return store.reserve(str(n), 'topic'+str(n), now, config, 'provider')


def test_restart_quota_shared_and_interval(tmp_path):
    path = tmp_path / 'p.db'
    for n in range(10):
        s = ProactiveState(path)
        now = START + timedelta(minutes=30*n)
        token = reserve(s, n, now)
        assert token
        assert s.mark_presenting(token, now)
        assert s.finish(token, '不同话题'+str(n), ['care'], now, True)
        assert not reserve(s, 'early'+str(n), now + timedelta(minutes=29))
    assert not reserve(ProactiveState(path), 11, START+timedelta(hours=8))
    assert ProactiveState(path).stats(START.date().isoformat())['successes'] == 10


def test_failed_display_and_cross_midnight(tmp_path):
    s = ProactiveState(tmp_path / 'p.db')
    now = START.replace(hour=23, minute=50)
    t = reserve(s, 1, now)
    s.mark_presenting(t, now)
    s.finish(t, '晚安', ['greeting'], now, False)
    assert s.stats(now.date().isoformat())['successes'] == 0
    t = reserve(s, 2, now)
    s.mark_presenting(t, now)
    s.finish(t, '晚上好', ['greeting'], now, True)
    assert not reserve(s, 3, now+timedelta(minutes=29))
    assert reserve(s, 3, now+timedelta(minutes=30))


def test_concurrent_last_slot(tmp_path):
    s = ProactiveState(tmp_path / 'p.db')
    cfg = {**CFG, 'daily_limit': 1}
    with ThreadPoolExecutor(8) as pool:
        tokens = list(pool.map(lambda n: reserve(s, n, config=cfg), range(8)))
    assert sum(bool(t) for t in tokens) == 1


def test_clock_backwards_timezone_and_dst(tmp_path):
    s = ProactiveState(tmp_path / 'p.db')
    t = reserve(s, 1)
    s.mark_presenting(t, START)
    s.finish(t, '好呀', ['care'], START, True)
    assert not reserve(s, 2, START-timedelta(days=1))
    assert not reserve(s, 2, START.astimezone(timezone(timedelta(hours=2))))
    assert reserve(s, 2, (START+timedelta(minutes=30)).astimezone(timezone(timedelta(hours=2))))


def test_attempt_budget_failures_and_401(tmp_path):
    s = ProactiveState(tmp_path / 'p.db')
    cfg = {**CFG, 'daily_limit': 1}
    for n in range(2):
        now = START+timedelta(hours=n)
        t = reserve(s, n, now, cfg)
        assert t
        s.release(t)
    assert not reserve(s, 3, START+timedelta(hours=3), cfg)
    assert s.stats(START.date().isoformat())['tokens'] == 192
    s.failure(401, 0, START, 'old')
    assert not s.reserve('auth', 'greeting', START+timedelta(days=1), CFG, 'old')
    assert s.reserve('auth', 'greeting', START+timedelta(days=1), CFG, 'new')


def test_corrupt_database_preserved(tmp_path):
    path = tmp_path / 'p.db'
    path.write_bytes(b'not sqlite')
    with pytest.raises(StateUnavailable):
        reserve(ProactiveState(path), 1)
    assert path.read_bytes() == b'not sqlite'


def test_crash_pending_expires_presenting_holds_slot(tmp_path):
    path = tmp_path/'p.db'
    cfg = {**CFG, 'daily_limit': 1}
    pending = reserve(ProactiveState(path), 1, config=cfg)
    assert pending
    s = ProactiveState(path)
    assert not reserve(s, 2, START+timedelta(seconds=59), cfg)
    token = reserve(s, 2, START+timedelta(seconds=60), cfg)
    assert token
    s.mark_presenting(token, START+timedelta(seconds=60))
    assert not reserve(ProactiveState(path), 3, START+timedelta(hours=4), cfg)
    assert s.stats(START.date().isoformat())['successes'] == 0
    assert reserve(s, 4, START+timedelta(days=1), cfg)


def test_429_backoff_and_once_only_receipt(tmp_path):
    s = ProactiveState(tmp_path/'p.db')
    s.failure(429, 3600, START, 'provider')
    assert not reserve(s, 1, START+timedelta(minutes=59))
    t = reserve(s, 1, START+timedelta(hours=1))
    assert t
    now = START+timedelta(hours=1)
    s.mark_presenting(t, now)
    assert s.finish(t, '测试台词', [], now, True)
    assert not s.finish(t, '测试台词', [], now, True)
    assert s.stats(now.date().isoformat())['successes'] == 1


def test_version_and_lock_fail_closed(tmp_path):
    import sqlite3
    path = tmp_path/'p.db'
    s = ProactiveState(path)
    assert reserve(s, 1)
    db = sqlite3.connect(path)
    db.execute('BEGIN EXCLUSIVE')
    try:
        with pytest.raises(StateUnavailable):
            reserve(s, 2)
    finally:
        db.rollback()
    db.execute('PRAGMA user_version=999')
    db.close()
    with pytest.raises(StateUnavailable):
        reserve(s, 3)
    db = sqlite3.connect(path)
    assert db.execute('PRAGMA user_version').fetchone()[0] == 999
    db.close()


def test_semantic_cooldown_persists_mixed_tags(tmp_path):
    s = ProactiveState(tmp_path/'p.db')
    t = s.reserve('morning', 'greeting', START, CFG, 'provider')
    s.mark_presenting(t, START)
    s.finish(t, '早呀！记得补充水分哦。', ['greeting', 'drink'], START, True)
    restart = ProactiveState(s.path)
    assert not restart.reserve('water', 'drink', START+timedelta(minutes=30), CFG, 'provider')
    assert restart.reserve('break', 'break', START+timedelta(minutes=30), CFG, 'provider')


def test_actual_second_process_cannot_reset_daily_quota(tmp_path):
    import subprocess
    import sys
    path = tmp_path/'p.db'
    s = ProactiveState(path)
    cfg = {**CFG, 'daily_limit': 1}
    token = reserve(s, 1, config=cfg)
    s.mark_presenting(token, START)
    s.finish(token, '合成测试台词', ['care'], START, True)
    code = "from pet.companion.proactive_state import ProactiveState;from datetime import datetime,timezone;import sys;s=ProactiveState(sys.argv[1]);assert s.stats('2026-10-12')['successes']==1;assert not s.reserve('new','drink',datetime(2026,10,12,16,tzinfo=timezone.utc),{'enabled':True,'daily_limit':1},'provider')"
    subprocess.run([sys.executable, '-c', code, str(path)], check=True, timeout=15)


@pytest.mark.parametrize('spring', [False, True])
def test_dst_wall_clock_change_uses_elapsed_utc(tmp_path, spring):
    s = ProactiveState(tmp_path/'p.db')
    if spring:
        before = datetime(2026, 3, 29, 1, 50, tzinfo=timezone(timedelta(hours=1)))
        after = datetime(2026, 3, 29, 3, 20, tzinfo=timezone(timedelta(hours=2)))
    else:
        before = datetime(2026, 10, 25, 2, 50, tzinfo=timezone(timedelta(hours=2)))
        after = datetime(2026, 10, 25, 2, 20, tzinfo=timezone(timedelta(hours=1)))
    token = reserve(s, 1, before)
    assert token
    s.mark_presenting(token, before)
    s.finish(token, 'DST合成测试', ['care'], before, True)
    assert not reserve(s, 2, after-timedelta(minutes=1))
    assert reserve(s, 2, after)
