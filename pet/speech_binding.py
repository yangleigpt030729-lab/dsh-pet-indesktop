"""One revocable audio task holds one exact text presentation (GUI thread only)."""
import time
import uuid
import weakref
import shiboken6
from PySide6.QtCore import QObject, QTimer

class SpeechTicket(QObject):
    WAIT_MS = 120000
    STALL_S = 180

    def __init__(self, bubble, receipt, valid):
        super().__init__(bubble)
        self.id = uuid.uuid4().hex
        self.bubble = weakref.ref(bubble)
        self.receipt = receipt
        self.guard = valid
        self.state = 'waiting'
        self.finished = False
        self.on_finish = None
        self.destroying = False
        self.speech_task = self
        self.last_progress = time.monotonic()
        self.position = -1
        self.watch = QTimer(self)
        self.watch.setInterval(250)
        self.watch.timeout.connect(self.check)
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(lambda: self.finish('timeout'))
        bubble.hidden_signal.connect(self.cancel)
        bubble.destroyed.connect(self._bubble_destroyed)
        bubble.presentation_replaced.connect(self.cancel)
        if bubble.begin_speech(receipt, self.id):
            self.watch.start()
            self.deadline.start(self.WAIT_MS)
        else:
            self.finish('cancelled')

    def __call__(self):
        b = self.bubble()
        try:
            return bool(not self.finished and b is not None and shiboken6.isValid(b)
                and b.isVisible() and b.text_presentation_id == self.receipt and self.guard())
        except (RuntimeError, AttributeError):
            return False

    def phase(self, state):
        if not self():
            self.finish('cancelled')
            return
        self.state = state
        if state == 'playing':
            self.deadline.stop()  # A healthy long recording has no absolute duration cap.
            self.last_progress = time.monotonic()
            self.bubble().speech_playing(self.receipt, self.id)

    def progress(self, duration, position):
        if not self():
            self.finish('cancelled')
            return
        if position != self.position:
            self.last_progress = time.monotonic()
            self.position = position
        self.bubble().speech_progress(self.receipt, self.id, duration, position)

    def check(self):
        if not self():
            self.finish('cancelled')
        elif self.state == 'playing' and time.monotonic()-self.last_progress > self.STALL_S:
            self.finish('timeout')

    def _bubble_destroyed(self):
        # QObject.destroyed can run after QWidget teardown while isValid still
        # reports true. Never call a widget method or re-delete its child here.
        self.destroying = True
        self.bubble = lambda: None
        self.finish('cancelled')

    def cancel(self):
        self.finish('cancelled')

    def finish(self, outcome):
        if self.finished:
            return
        if outcome == "completed" and not self():
            outcome = "cancelled"
        self.finished = True
        self.state = outcome
        self.watch.stop()
        self.deadline.stop()
        b = self.bubble()
        if b is not None and shiboken6.isValid(b):
            b.end_speech(self.receipt, self.id, outcome == 'completed')
            try:
                b.hidden_signal.disconnect(self.cancel)
                b.destroyed.disconnect(self._bubble_destroyed)
                b.presentation_replaced.disconnect(self.cancel)
            except (RuntimeError, TypeError):
                pass
        if self.on_finish is not None:
            callback, self.on_finish = self.on_finish, None
            callback(outcome)
        if not self.destroying:
            self.deleteLater()


def phase(valid, state):
    task = getattr(valid, 'speech_task', None)
    if task is not None and not task.finished:
        task.phase(state)


def finish(valid, outcome):
    task = getattr(valid, 'speech_task', None)
    if task is not None:
        task.finish(outcome)


def bind_displayed(host, text, valid):
    """For independent chime/festival consumers, without companion opt-in coupling."""
    bubble = getattr(host, '_speech_bubble', None)
    if bubble is None or not shiboken6.isValid(bubble):
        return None
    receipt = bubble.text_presentation_id
    if not bubble.text_was_presented(text, receipt-1):
        return None
    ref = weakref.ref(host)
    def current():
        owner = ref()
        from .voice_volume import effective
        config = getattr(owner, "cfg", None)
        return (owner is not None and owner.isVisible() and valid()
                and (config is None or effective(config) > 0))
    return SpeechTicket(bubble, receipt, current)
