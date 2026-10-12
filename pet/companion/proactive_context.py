"""Read-only worker context: no synthetic user facts, sessions, or completion writes."""
from .memory_store import MemoryStore, MemoryUnavailable
from ..chat.prompt import memory_message


class ReadOnlyMemory:
    def __init__(self, policy, enabled):
        self.policy = policy
        self.enabled = enabled
        self.revision = None
        self.stamp = None

    def prepare(self, messages):
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
