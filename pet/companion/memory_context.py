"""Chat worker boundary: all SQLite and extraction work stays off the Qt UI thread."""
from dataclasses import dataclass
import json
import logging
import threading
from pathlib import Path
from .memory_extract import extract_memories
from .memory_store import MemoryStore, MemoryUnavailable

log = logging.getLogger(__name__)
_policy_lock = threading.Lock()
_runtime_policies = {}


def _runtime_policy(path):
    with _policy_lock:
        return _runtime_policies.get(str(path), (0, None))


@dataclass(frozen=True)
class MemoryContext:
    path: Path
    user_text: str
    enabled: bool = False
    automatic: bool = False
    policy_path: Path | None = None
    generation: int = 0

    @staticmethod
    def set_runtime_policy(path, enabled):
        with _policy_lock:
            generation = _runtime_policies.get(str(path), (0, None))[0]
            _runtime_policies[str(path)] = (generation + 1, enabled)

    @classmethod
    def from_config(cls, config, user_text):
        settings = config.chat_settings()
        return cls(config.dir / 'companion_memory.sqlite3', user_text,
                   settings.memory_enabled, settings.memory_auto_extract, config.path,
                   _runtime_policy(config.path)[0])

    def _policy(self):
        if not self.enabled:
            return False, False, None
        if self.policy_path is None:
            return True, self.automatic, None
        generation, runtime_enabled = _runtime_policy(self.policy_path)
        if generation != self.generation or runtime_enabled is False:
            return False, False, None
        try:
            # Read a stable on-disk policy, never a mutable QObject/config on the worker.
            stamp = self.policy_path.stat().st_mtime_ns
            data = json.loads(self.policy_path.read_text(encoding='utf-8')).get('chat', {})
            return data.get('memory_enabled') is True, data.get('memory_auto_extract') is True, stamp
        except (OSError, ValueError, AttributeError):
            return False, False, None

    def prepare(self, messages):
        enabled, automatic, stamp = self._policy()
        if not enabled:
            return messages, None
        try:
            store = MemoryStore(self.path)
            revision = store.revision()
            rows = store.search(self.user_text)
            from ..chat.prompt import memory_message
            quoted = memory_message([f'{r.content}（记录日期：{r.updated_at[:10]}）' for r in rows], include_empty=True)
            # A consent change while SQLite was waiting must not leak the prepared context.
            current_enabled, _, current_stamp = self._policy()
            if not current_enabled or current_stamp != stamp:
                return messages, None
            augmented = [messages[0], quoted, *messages[1:]] if quoted and messages else messages
            return augmented, (revision, automatic, stamp)
        except (MemoryUnavailable, ValueError):
            log.warning('长期记忆暂不可用；本次继续普通聊天。')
            return messages, None

    def completed(self, token):
        if token is None:
            return
        enabled, automatic, stamp = self._policy()
        revision, originally_automatic, original_stamp = token
        if not enabled or stamp != original_stamp:
            return
        candidates = extract_memories(self.user_text, automatic and originally_automatic)
        if not candidates:
            return
        try:
            MemoryStore(self.path).remember(candidates, revision, allowed=lambda: self._policy()[0] and self._policy()[2] == original_stamp)
        except (MemoryUnavailable, ValueError):
            log.warning('长期记忆保存失败；聊天结果不受影响。')
