from datetime import datetime, timedelta
import pytest
from pet.todo_reminder import TodoReminderService, TodoStore, new_todo_item
from tests.test_todo_reminder import _FakeApp, _qapp

NOW = datetime(2026, 10, 13, 10, 0)


def setup(tmp_path):
    _qapp()
    app = _FakeApp(tmp_path)
    app.config.set('todo_reminder_lead_minutes', 0)
    app.config.set('system_notifications_enabled', False)
    s = TodoReminderService(app)
    s.set_items([new_todo_item('合成到期任务', 'once', '10:00', '2026-10-13')])
    s.apply_config()
    return app, s


def test_failed_presentation_is_not_stamped_and_retries_after_restart(tmp_path):
    app, s = setup(tmp_path)
    app.win.try_show_bubble = lambda *a, **k: False
    s._on_tick(NOW)
    assert s._store.load()[0]['fired_due_slot'] is None
    s.stop()
    new = TodoReminderService(app)
    new.apply_config()
    app.win.try_show_bubble = lambda *a, **k: True
    new._on_tick(NOW+timedelta(minutes=1))
    assert new._store.load()[0]['fired_due_slot'] == '2026-10-13T10:00#due'
    new.stop()


def test_write_failure_never_displays_unreserved_reminder(tmp_path, monkeypatch):
    app, s = setup(tmp_path)
    monkeypatch.setattr(s._store, 'save', lambda _: False)
    s._on_tick(NOW)
    assert app.win.bubbles == []
    s.stop()


def test_delivered_receipt_write_failure_does_not_repeat_in_same_process(tmp_path, monkeypatch):
    app, s = setup(tmp_path)
    original = s._store.save
    writes = []
    def save(items):
        writes.append(True)
        return original(items) if len(writes) == 1 else False
    monkeypatch.setattr(s._store, 'save', save)
    s._on_tick(NOW)
    s._on_tick(NOW+timedelta(seconds=30))
    assert len(app.win.bubbles) == 1
    monkeypatch.setattr(s._store, 'save', original)
    s._on_tick(NOW+timedelta(minutes=1))
    assert len(app.win.bubbles) == 1
    assert s._store.load()[0]['fired_due_slot']
    s.stop()


@pytest.mark.parametrize('operation', ['delete', 'disable', 'edit'])
def test_pending_reminder_cannot_revive_after_panel_change(tmp_path, operation):
    app, s = setup(tmp_path)
    app.win.try_show_bubble = lambda *a, **k: False
    s._on_tick(NOW)
    items = s.items()
    if operation == 'delete':
        items = []
    elif operation == 'disable':
        items[0]['enabled'] = False
    else:
        items[0]['time'] = '11:00'
    s.set_items(items)
    app.win.try_show_bubble = lambda *a, **k: pytest.fail('Canceled task revived')
    s._on_tick(NOW+timedelta(minutes=1))
    s.stop()


def test_two_services_share_one_persistent_delivery_receipt(tmp_path):
    app, s = setup(tmp_path)
    second = TodoReminderService(app)
    second.apply_config()
    s._on_tick(NOW)
    second._on_tick(NOW)
    assert len(app.win.bubbles) == 1
    s.stop()
    second.stop()


def test_missed_beyond_grace_stays_compatible_and_no_resurrection(tmp_path):
    app, s = setup(tmp_path)
    s._on_tick(NOW+timedelta(days=3))
    assert not app.win.bubbles
    assert s._store.load()[0]['enabled'] is False
    s._on_tick(NOW)
    assert not app.win.bubbles
    s.stop()


def test_daily_catchup_after_midnight_is_within_existing_grace(tmp_path):
    app, s = setup(tmp_path)
    s.set_items([new_todo_item('合成午夜提醒', 'daily', '23:58')])
    s._on_tick(datetime(2026, 10, 14, 0, 2))
    assert len(app.win.bubbles) == 1
    s._on_tick(datetime(2026, 10, 14, 0, 3))
    assert len(app.win.bubbles) == 1
    s.stop()


def test_timer_disk_work_is_off_gui_thread_and_stop_cancels_display(tmp_path, monkeypatch):
    import threading
    import time
    from tests.test_companion_chat import wait
    app, s = setup(tmp_path)
    qt = _qapp()
    started, release = threading.Event(), threading.Event()
    original = s._store.save
    threads = []
    def save(items):
        threads.append(threading.current_thread())
        started.set()
        release.wait(10)
        return original(items)
    monkeypatch.setattr(s._store, 'save', save)
    before = time.monotonic()
    try:
        s.request_tick(NOW)
        assert time.monotonic()-before < 1
        wait(qt, started.is_set)
        assert threads[0] is not threading.main_thread()
        s.stop()
        release.set()
        wait(qt, lambda: not s.busy)
        assert not app.win.bubbles
    finally:
        release.set()
        s.stop()


def test_delete_during_reserved_disk_write_survives_busy_file_lock(tmp_path, monkeypatch):
    import threading
    from tests.test_companion_chat import wait
    app, s = setup(tmp_path)
    qt = _qapp()
    started, release = threading.Event(), threading.Event()
    original = s._store._save_atomic
    def blocked(items):
        started.set()
        release.wait(10)
        return original(items)
    monkeypatch.setattr(s._store, '_save_atomic', blocked)
    try:
        s.request_tick(NOW)
        wait(qt, started.is_set)
        assert s.set_items([]) is False  # Busy transaction: preserve edit, never overwrite it.
        release.set()
        wait(qt, lambda: not s.busy)
        assert not app.win.bubbles and s.items() == []
        s.request_tick(NOW+timedelta(seconds=30))
        wait(qt, lambda: not s.busy)
        assert s._store.load() == [] and not app.win.bubbles
    finally:
        release.set()
        s.stop()


def test_delayed_gui_handoff_cannot_show_expired_or_clock_reversed_claim(tmp_path, monkeypatch):
    from pet.todo_delivery import reserve
    app, s = setup(tmp_path)
    fires = reserve(s._store, s._prefs, NOW)
    assert len(fires) == 1
    # A queued callback arriving after sleep or clock rollback must recheck time.
    monkeypatch.setattr(s._disk, 'clock', lambda: NOW+timedelta(minutes=11), raising=False)
    s._disk._receive(('prepare', s._disk.generation, ([], fires, s._store.load(), False)))
    from tests.test_companion_chat import wait
    wait(_qapp(), lambda: not s.busy)
    assert app.win.bubbles == []
    fires = reserve(s._store, s._prefs, NOW+timedelta(seconds=31))
    monkeypatch.setattr(s._disk, 'clock', lambda: NOW-timedelta(minutes=1), raising=False)
    s._disk._receive(('prepare', s._disk.generation, ([], fires, s._store.load(), False)))
    wait(_qapp(), lambda: not s.busy)
    assert app.win.bubbles == []
    s.stop()
