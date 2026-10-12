"""Read-only worker context: no synthetic user facts, sessions, or completion writes."""
from .memory_store import MemoryStore, MemoryUnavailable
from ..chat.prompt import memory_message
from datetime import datetime


class ReadOnlyMemory:
    def __init__(self, policy, enabled, *, window=None, clock=None):
        self.policy = policy
        self.enabled = enabled
        self.revision = None
        self.stamp = None
        self.window = window
        self.clock = clock or (lambda: datetime.now().astimezone())

    def request_valid(self):
        if self.window is None:
            return True
        now = self.clock()
        return now.date().isoformat() == self.window['day'] and now.timestamp() < self.window['expires']

    def prepare(self, messages):
        if not self.request_valid():
            raise ValueError('proactive request window expired')
        result = self._prepare(messages)
        if not self.request_valid():
            raise ValueError('proactive request window expired')
        return result

    def _prepare(self, messages):
        enabled, _, stamp = self.policy._policy()
        if not self.enabled or not enabled:
            return messages, None
        try:
            if not self.policy.path.is_file():
                return messages, None
            store = MemoryStore(self.policy.path)
            revision = store.revision()
            rows = store.search('你还记得我告诉过你什么吗', limit=3, char_limit=300)
            if store.revision() != revision or not self.policy._policy()[0] or stamp != self.policy._policy()[2]:
                return messages, None
            self.revision, self.stamp = revision, stamp
            quoted = memory_message([f'{r.content}（记录日期：{r.updated_at[:10]}）' for r in rows])
            return ([messages[0], quoted, *messages[1:]] if quoted else messages), None
        except MemoryUnavailable:
            return messages, None

    def valid(self):
        if self.revision is None:
            return True
        enabled, _, stamp = self.policy._policy()
        if not enabled or stamp != self.stamp:
            return False
        try:
            return MemoryStore(self.policy.path).revision() == self.revision
        except MemoryUnavailable:
            return False

    def completed(self, token):
        # ChatService's optional context contract; intentionally never invokes
        # MemoryContext.completed and never extracts the model's own words.
        pass
