"""Delivery claims in the existing bounded TodoStore JSON, never a second scheduler.

Claims are saved before UI presentation, receipts afterwards. An interrupted UI
handoff can be retried after 30 seconds within the existing ten-minute grace;
exactly-once display across a process crash cannot be atomic with a JSON file.
"""
from contextlib import contextmanager
import hashlib
import json
import uuid
import copy


def signature(item):
    return hashlib.sha256(json.dumps([item.get(k) for k in
        ('id', 'title', 'kind', 'date', 'time')], ensure_ascii=False).encode()).hexdigest()


@contextmanager
def locked(store):
    if getattr(store._transaction, 'active', False):
        yield True
        return
    from PySide6.QtCore import QLockFile
    store.path.parent.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(store.path)+'.lock')
    lock.setStaleLockTime(30000)
    try:
        acquired = lock.tryLock(0)
        store._transaction.active = acquired
        yield acquired
    finally:
        store._transaction.active = False
        lock.unlock()


def reserve(store, prefs, now, excluded=()):
    from .todo_reminder import advance_todo_state
    with locked(store) as acquired:
        if not acquired:
            return []
        items = store.load()
        fires, proposed = advance_todo_state(items, prefs, now)
        proposed = copy.deepcopy(proposed)
        previous = {i['id']: i for i in items}
        due_ids = {f['id'] for f in fires if f['phase'] == 'due'}
        claims = []
        for fire in fires:
            item = next(i for i in proposed if i['id'] == fire['id'])
            if fire['phase'] == 'lead' and fire['id'] in due_ids:
                continue  # A due reminder subsumes its late advance reminder.
            phase = fire['phase']
            slot_key = 'fired_'+phase+'_slot'
            slot = item[slot_key]
            item[slot_key] = previous[item['id']].get(slot_key)
            sig = signature(item)
            event = (item['id'], phase, slot, sig)
            state = previous[item['id']].get('delivery', {}).get(phase, {})
            if event in excluded or (state.get('slot') == slot and state.get('signature') == sig
                                      and state.get('lease', 0) > now.timestamp()):
                continue
            claim = {**fire, 'slot': slot, 'signature': sig, 'token': uuid.uuid4().hex}
            item.setdefault('delivery', {})[phase] = {
                'slot': slot, 'signature': sig, 'token': claim['token'],
                'status': 'presenting', 'lease': now.timestamp()+30}
            claims.append(claim)
        if proposed != items and not store.save(proposed):
            return []
        return claims


def finish(store, fire, shown):
    with locked(store) as acquired:
        if not acquired:
            return False
        items = store.load()
        item = next((i for i in items if i['id'] == fire['id']), None)
        if not item or not item['enabled'] or signature(item) != fire['signature']:
            return True  # A canceled/edited task is never resurrected.
        state = item.get('delivery', {}).get(fire['phase'], {})
        if state.get('token') != fire['token']:
            return True
        if shown:
            item['fired_'+fire['phase']+'_slot'] = fire['slot']
            state['status'] = 'delivered'
        else:
            state['status'] = 'pending'
        state['lease'] = 0
        return store.save(items)


def event_key(fire):
    return tuple(fire[k] for k in ('id', 'phase', 'slot', 'signature'))
