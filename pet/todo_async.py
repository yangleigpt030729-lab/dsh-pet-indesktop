"""One bounded disk worker for the existing TodoReminderService timer."""
from concurrent.futures import ThreadPoolExecutor
import weakref
import copy
from datetime import datetime
import shiboken6
from PySide6.QtCore import QObject, Signal, Qt
from .todo_delivery import reserve, finish, event_key, signature


class TodoDiskWorker(QObject):
    ready = Signal(object)

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.pool = ThreadPoolExecutor(1, thread_name_prefix='pet-todo-disk')
        self.generation = 0
        self.busy = False
        self.closed = False
        self.clock = datetime.now
        self.ready.connect(self._receive, Qt.QueuedConnection)

    def submit(self, action, phase, generation):
        ref = weakref.ref(self)
        def complete(future):
            obj = ref()
            if obj is None or not shiboken6.isValid(obj):
                return
            try:
                result = future.result()
            except Exception:
                result = None
            try:
                obj.ready.emit((phase, generation, result))
            except RuntimeError:
                pass
        self.pool.submit(action).add_done_callback(complete)

    def request(self, now):
        owner = self.owner
        if self.busy or self.closed or not owner._prefs['enabled']:
            return
        self.busy = True
        prefs, confirmed = dict(owner._prefs), dict(owner._confirmed)
        pending = copy.deepcopy(owner._pending_items)
        def prepare():
            if pending is not None and not owner._store.save(pending):
                return [], [], None, False
            settled = [key for key, fire in confirmed.items() if finish(owner._store, fire, True)]
            fires = reserve(owner._store, prefs, now, confirmed)
            return settled, fires, owner._store.load(), pending is not None
        self.submit(prepare, 'prepare', self.generation)

    def _receive(self, payload):
        phase, generation, result = payload
        owner = self.owner
        if phase == 'prepare':
            settled, fires, items, flushed = result if result else ([], [], None, False)
            for key in settled:
                owner._confirmed.pop(key, None)
            receipts = []
            for fire in fires:
                item = next((i for i in owner._items if i['id'] == fire['id']), None)
                current_time = self.clock().timestamp()
                allowed = (not self.closed and generation == self.generation and owner._prefs['enabled']
                           and item and item['enabled'] and signature(item) == fire['signature']
                           and fire['not_before'] <= current_time <= fire['expires'])
                try:
                    shown = bool(allowed and owner._notify_fire(fire))
                except Exception:
                    shown = False
                if shown:
                    owner._confirmed[event_key(fire)] = fire
                receipts.append((fire, shown))
            if not self.closed and generation == self.generation:
                if items is not None:
                    owner._items = items
                if flushed:
                    owner._pending_items = None
            if receipts:
                def settle():
                    return [event_key(fire) for fire, shown in receipts if finish(owner._store, fire, shown)]
                # stop() has already shut the pool; these claims expire within grace.
                if not self.closed:
                    self.submit(settle, 'settle', generation)
                    return
        elif result:
            for key in result:
                owner._confirmed.pop(key, None)
        self.busy = False

    def close(self):
        self.generation += 1
        self.closed = True
        self.pool.shutdown(wait=False, cancel_futures=True)
