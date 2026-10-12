"""One process-wide bounded daemon worker for feed metadata and original statistics."""
from queue import Queue, Full
from threading import Thread, Lock, Event
from datetime import datetime
import weakref
import shiboken6
from PySide6.QtCore import QObject, Signal, Qt, QEvent
from . import feeding_metadata

_QUEUE = Queue(maxsize=32)
_LOCK = Lock()
_STARTED = False


def _run():
    while True:
        ref, paths, stats_path, cancel, context = _QUEUE.get()
        result = None
        try:
            if not cancel.is_set():
                result = feeding_metadata.describe(paths, cancel)
            if result is not None and not cancel.is_set():
                from ..file_eater import _default_stats, _load_stats, _save_stats, STATS_HISTORY_LIMIT
                stats = _load_stats(stats_path) if stats_path else _default_stats()
                stats['feed_count'] += 1
                stats['file_count'] += result['files']
                stats['folder_count'] += result['folders']
                stats['item_count'] += result['files']+result['folders']
                stats['total_bytes'] += result['bytes']
                stats['size_partial_count'] = stats.get('size_partial_count', 0)+int(result['partial'])
                stats['history'].append({'time': datetime.now().isoformat(timespec='seconds'),
                    **{k: result[k] for k in ('files', 'folders', 'bytes', 'partial')}})
                del stats['history'][:-STATS_HISTORY_LIMIT]
                if stats_path and not cancel.is_set():
                    _save_stats(stats_path, stats)
                result['stats'] = stats
        except Exception:
            result = None  # Never print raw paths or file metadata.
        finally:
            worker = ref()
            if worker is not None and shiboken6.isValid(worker):
                try:
                    worker.completed.emit((result, paths, context))
                except RuntimeError:
                    pass
            _QUEUE.task_done()


class FeedWorker(QObject):
    completed = Signal(object)

    def __init__(self, parent, callback, stats_path):
        super().__init__(parent)
        self.cancel = Event()
        self.stats_path = stats_path
        self.pending = 0
        self.completed.connect(self._receive, Qt.QueuedConnection)
        self.callback = callback
        parent.installEventFilter(self)
        self.destroyed.connect(lambda *_: self.cancel.set())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Close:
            self.cancel.set()
        return False

    def submit(self, paths, context=None):
        global _STARTED
        if self.cancel.is_set():
            return False
        with _LOCK:
            if not _STARTED:
                Thread(target=_run, name='pet-feed-metadata', daemon=True).start()
                _STARTED = True
        try:
            _QUEUE.put_nowait((weakref.ref(self), tuple(str(p) for p in paths), self.stats_path, self.cancel, context))
        except Full:
            return False
        self.pending += 1
        return True

    def _receive(self, payload):
        self.pending = max(0, self.pending-1)
        if not self.cancel.is_set() and payload[0] is not None:
            self.callback(*payload)
