"""One ephemeral AI channel for explicit touch/feed events; no sessions or writes."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from collections import deque
from pathlib import Path
import json
import random
import time
import weakref
import shiboken6
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from ..chat.service import ChatService
from ..chat.models import SecretStore
from ..chat.prompt import PromptBuilder
from .memory_context import MemoryContext
from .proactive_context import ReadOnlyMemory
from .memory_extract import sensitive
from .proactive_repeat import text_key
from .interaction_config import enabled
from .memory_retrieve import tokens
from .expression_style import context as style_context, message as style_message, fallback_choices
from .head_speech import permission_stamp

_LIVE = set()
KIND_KEYS = {'head': 'head_touch_enabled', 'feeding': 'feeding_enabled'}
CATEGORIES = {'image', 'python', 'code', 'audio', 'video', 'archive', 'document', 'folder', 'other'}


def safe_metadata(raw):
    raw = raw if isinstance(raw, dict) else {}
    categories = raw.get('categories', {})
    return {'categories': {k: min(9999, max(0, v)) for k, v in categories.items()
                           if k in CATEGORIES and type(v) is int} if isinstance(categories, dict) else {},
            **{k: min(9999, max(0, raw[k])) if type(raw.get(k)) is int else 0 for k in ('files', 'folders')},
            'size_bucket': raw.get('size_bucket') if raw.get('size_bucket') in ('unknown', 'tiny', 'small', 'medium', 'large') else 'unknown'}


class InteractionService(QObject):
    delivered = Signal(str, str)
    status_changed = Signal(str)
    ready = Signal(object)

    def __init__(self, *, provider=None, parent=None, monotonic=None):
        super().__init__(parent)
        self.chat = ChatService(provider, notify_global=False)
        self.fake = provider is not None or getattr(self.chat.provider, 'synthetic_acceptance', False)
        self.pool = ThreadPoolExecutor(1, thread_name_prefix='pet-interaction')
        self.clock = monotonic or time.monotonic
        self.generation = self.jobs = 0
        self.closed = False
        self.active = None
        self.backoff = 0
        self.recent = deque(maxlen=12)
        self.ready.connect(self._dispatch, Qt.QueuedConnection)
        self.chat.finished.connect(self._result)
        self.chat.error.connect(self._error)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(25000)
        self.timer.timeout.connect(lambda: self._error(None, ''))
        self.feed_timer = QTimer(self)
        self.feed_timer.setSingleShot(True)
        self.feed_timer.timeout.connect(self._flush_feeding)
        self.pending_feeds = {}
        self._manual = self.cancel
        ChatService._global_started_listeners.append(self._manual)

    @property
    def busy(self):
        return bool(self.jobs or self.active or self.chat.busy or self.pending_feeds)

    def offer_feeding(self, target, metadata):
        if self.closed or not target.valid() or not enabled(target.config(), 'feeding_enabled'):
            return
        meta = safe_metadata(metadata)
        if self.active and self.active['target'].key == target.key:
            self.active['superseded'] = True  # New statistics own the bubble; finish the single flight quietly.
        old = self.pending_feeds.get(target.key)
        if old and old['identity'] == target.identity():
            previous = old['metadata']
            meta = safe_metadata({
                'files': meta['files']+previous['files'], 'folders': meta['folders']+previous['folders'],
                'categories': {k: meta['categories'].get(k, 0)+previous['categories'].get(k, 0)
                               for k in CATEGORIES}, 'size_bucket': 'unknown'})
        if target.key not in self.pending_feeds and len(self.pending_feeds) >= 32:
            return
        self.pending_feeds[target.key] = dict(target=target, metadata=meta, identity=target.identity(),
                                             expires=self.clock()+30, not_before=self.clock()+2)
        self.feed_timer.start(750)

    def _flush_feeding(self):
        now = self.clock()
        for key, entry in list(self.pending_feeds.items()):
            target = entry['target']
            if (not target.valid() or target.identity() != entry['identity'] or now >= entry['expires']
                    or not enabled(target.config(), 'feeding_enabled')):
                self.pending_feeds.pop(key, None)
                continue
            if (now < entry['not_before'] or self.jobs or self.active or self.chat.busy
                    or target.manual_busy()):
                continue
            self.pending_feeds.pop(key, None)
            # Other targets awaiting their turn must not block this request.
            remaining, self.pending_feeds = self.pending_feeds, {}
            self.request('feeding', target, entry['metadata'])
            self.pending_feeds = remaining
            break
        if self.pending_feeds:
            self.feed_timer.start(1000)

    def _submit(self, action, callback):
        if self.closed:
            return
        generation = self.generation
        self.jobs += 1
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
                obj.ready.emit((generation, callback, result))
            except RuntimeError:
                pass
        self.pool.submit(action).add_done_callback(complete)

    def _dispatch(self, payload):
        generation, callback, result = payload
        self.jobs = max(0, self.jobs-1)
        if not self.closed and generation == self.generation:
            callback(result)

    def request(self, kind, target, metadata=None):
        if kind not in KIND_KEYS or self.closed or not target.valid():
            return False
        cfg = target.config()
        if not enabled(cfg, KIND_KEYS[kind]):
            return False
        now = self.clock()
        # Successful completion has no timed cooldown. Busy head gestures are
        # consumed without queueing; feeding has its separate bounded merge.
        if self.busy or target.manual_busy():
            return False
        self.generation += 1  # A new interaction revokes unplayed audio from the previous event.
        settings = cfg.chat_settings()
        character = str(cfg.get('character', ''))
        self.active = {'kind': kind, 'target': target, 'identity': target.identity(),
                       'metadata': safe_metadata(metadata), 'style': style_context(cfg),
                       'consent': permission_stamp(cfg)}
        style = self.active['style']
        self.rid = None
        self.timer.start()
        policy = MemoryContext.from_config(cfg, '')
        use_memory = kind == 'head' and settings.memory_enabled
        provider = replace(settings.active_config, max_tokens=96, timeout=min(20, settings.active_config.timeout))
        def prepare():
            if not settings.enabled or now < self.backoff:
                return None
            if not self.fake and not provider.api_key:
                provider.api_key = SecretStore().get(provider.api_key_ref)
            if not self.fake and (not provider.api_key or not provider.base_url or not provider.model):
                return None
            prompt = PromptBuilder(Path(__file__).resolve().parents[2]/'assets'/'characters').effective_system_prompt(settings, character)
            task = ('用户明确单击了头部核心，请用当前角色生成自然的开心、撒娇或害羞回应。' if kind == 'head' else
                    '用户刚投喂了文件。只按下面的安全类别统计作食物比喻，绝不假装看过图片、读过代码或听过音频。')
            messages = [{'role': 'system', 'content': prompt}, style_message(style), {'role': 'system', 'content':
                '内部交互事件，不是用户聊天，不提取为用户事实。只回复1至2句中文、最多80字，不调用工具或语音。'
                +task+json.dumps({'interaction': kind, 'metadata': safe_metadata(metadata)}, ensure_ascii=False)}]
            return messages, provider, ReadOnlyMemory(policy, use_memory)
        self._submit(prepare, self._prepared)
        return True

    def _current(self):
        r = self.active
        if not r:
            return False
        t = r['target']
        return (t.valid() and not t.manual_busy() and t.identity() == r['identity']
                and (r['kind'] != 'head' or permission_stamp(t.config()) == r['consent'])
                and style_context(t.config()) == r['style'] and enabled(t.config(), KIND_KEYS[r['kind']]))

    def _prepared(self, result):
        if self.active and self.active.get('superseded'):
            self.timer.stop()
            self.active = None
            return  # Keep the bounded merged followup; avoid an obsolete paid request.
        if not self._current():
            self.cancel()
            return
        if result is None:
            self._fallback()
            return
        messages, provider, context = result
        self.active['context'] = context
        self.rid = self.chat.send(messages, provider, memory_context=context, output_limit=256)

    def _result(self, rid, text):
        if not self.active or rid != getattr(self, 'rid', None):
            return
        context = self.active['context']
        text = str(text).strip()
        if not text or len(text) > 80 or sensitive(text):
            self._fallback()
            return
        key, parts = text_key(text), tokens(text_key(text))
        if any(key == old or (parts and len(parts & tokens(old))/max(1, len(parts | tokens(old))) >= .65)
               for old in self.recent):
            self._fallback()
            return
        self._submit(lambda: context.valid(), lambda valid: self._present(text) if valid else self.cancel())

    def _present(self, text):
        if self._current() and not self.active.get('superseded') and self.active['target'].present(text):
            target, kind = self.active['target'], self.active['kind']
            identity, generation, expires = target.identity(), self.generation, self.clock()+30
            consent = self.active['consent']
            self.recent.append(text_key(text))
            self.delivered.emit(kind, text)
            if kind in KIND_KEYS:
                from .head_speech import speech_enabled, speak_target
                owner = weakref.ref(self)
                def valid():
                    service = owner()
                    return bool(service is not None and shiboken6.isValid(service) and not service.closed and service.generation == generation
                        and service.clock() < expires and target.valid() and target.identity() == identity
                        and permission_stamp(target.config()) == consent
                        and enabled(target.config(), KIND_KEYS[kind]) and speech_enabled(target.config()))
                if hasattr(target, 'host_ref'):
                    speak_target(target, text, valid)
        self.timer.stop()
        self.active = None

    def _fallback(self):
        if not self.active:
            return
        choices = fallback_choices(self.active['style'], self.active['kind'], self.active['metadata'])
        choices = [t for t in choices if text_key(t) not in self.recent] or choices
        text = random.choice(choices)
        self._present(('合成测试：' if self.fake else '')+text)

    def _error(self, rid, _message):
        if self.active and (rid is None or rid == getattr(self, 'rid', None)):
            self.backoff = self.clock()+120
            self.chat.stop()
            self.status_changed.emit('交互模型暂不可用；已退避并使用本地文字')
            self._fallback()

    def cancel(self):
        self.generation += 1
        self.timer.stop()
        self.chat.stop()
        self.active = None
        self.feed_timer.stop()
        self.pending_feeds.clear()

    def close(self):
        if self.closed:
            return
        self.cancel()
        self.closed = True
        if self._manual in ChatService._global_started_listeners:
            ChatService._global_started_listeners.remove(self._manual)
        self.pool.shutdown(wait=False, cancel_futures=True)
        if self.chat._workers:
            _LIVE.add(self)
            for worker in list(self.chat._workers):
                worker.finished.connect(self._release, Qt.QueuedConnection)

    def _release(self):
        if not any(w.isRunning() for w in self.chat._workers):
            _LIVE.discard(self)
