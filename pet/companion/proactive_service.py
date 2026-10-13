"""One process-level opt-in companion service, using the existing ChatService.

Qt snapshots/presentation stay on the GUI thread. SQLite, credential resolution,
role loading and response classification use one bounded background executor.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from pathlib import Path
import hashlib
import json
import time
import weakref

import shiboken6
from PySide6.QtCore import QObject, QTimer, Qt, Signal
from ..chat.models import SecretStore
from ..chat.prompt import PromptBuilder
from ..chat.service import ChatService
from .memory_context import MemoryContext
from .memory_extract import sensitive
from .proactive_config import normalize_config
from .proactive_policy import policy
from .proactive_context import ReadOnlyMemory
from .proactive_repeat import classify, repeats, provider_history_summary
from .proactive_schedule import Scheduler
from .proactive_state import ProactiveState
from .expression_style import context as style_context, message as style_message

_LIVE = set()  # Pin canceled/uninterruptible QThreads until they finish.


class ProactiveService(QObject):
    delivered = Signal(str)
    status_changed = Signal(str)
    _done = Signal(object)

    def __init__(self, config, snapshot, present, *, provider=None, parent=None, clock=None, monotonic=None):
        super().__init__(parent)
        self.config, self.snapshot, self.present = config, snapshot, present
        self.clock = clock or (lambda: datetime.now().astimezone())
        self.monotonic = monotonic or time.monotonic
        self.state = ProactiveState(config.dir / 'companion_proactive.sqlite3')
        self.scheduler = Scheduler()
        self.chat = ChatService(provider, notify_global=False)
        self.fake = provider is not None
        self.pool = ThreadPoolExecutor(1, thread_name_prefix='pet-companion')
        self.generation, self.jobs = 0, 0
        self.token = None
        self.closed = False
        self.status = '尚未启用'
        self.identity = None
        self.unavailable = None
        self.last_mono = None
        self.failure = {}
        self.context = None
        self._done.connect(self._dispatch, Qt.QueuedConnection)
        self.timer = QTimer(self)
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.tick)
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.setInterval(25000)
        self.deadline.timeout.connect(self._timeout)
        self.chat.finished.connect(self._result)
        self.chat.error.connect(self._error)
        self.chat.failure_info.connect(self._failure_info)
        self._manual_callback = self.cancel
        ChatService._global_started_listeners.append(self._manual_callback)
        self.apply_config()

    @property
    def busy(self):
        return bool(self.jobs or self.token or self.chat.busy)

    def _settings(self):
        cfg = normalize_config(self.config.get('proactive_chat'))
        generation, runtime_enabled = policy(self.config.path)
        if runtime_enabled is False:
            cfg['enabled'] = False
        settings = self.config.chat_settings()
        character = str(self.config.get('character', ''))
        try:
            stamp = self.config.path.stat().st_mtime_ns
        except OSError:
            stamp = 0
        identity = hashlib.sha256(json.dumps([cfg, settings.to_dict(), character, stamp, generation, style_context(self.config)], sort_keys=True).encode()).hexdigest()
        return cfg, settings, character, identity

    def _status(self, text):
        self.status = text
        self.status_changed.emit(text)

    def apply_config(self):
        cfg, _, _, identity = self._settings()
        if identity != self.identity:
            self.cancel()
            self.identity = identity
            self.unavailable = None
        if cfg['enabled'] and not self.closed:
            if not self.timer.isActive():
                self.timer.start()
            self._status('等待合适时机；到期待办由原待办提醒独立投递')
        else:
            self.timer.stop()
            self._status('已关闭；不会安排主动请求')

    def _submit(self, action, callback, generation=None):
        if self.closed:
            return
        self.jobs += 1
        generation = self.generation if generation is None else generation
        ref = weakref.ref(self)
        def done(future):
            owner = ref()
            if owner is not None and shiboken6.isValid(owner):
                try:
                    result = future.result()
                except Exception:
                    result = None  # Never log provider exception bodies or private data.
                owner._done.emit((callback, result, generation))
        self.pool.submit(action).add_done_callback(done)

    def _dispatch(self, payload):
        callback, result, generation = payload
        self.jobs = max(0, self.jobs-1)
        callback(result, generation)

    def tick(self, *, category=None):
        if self.closed:
            return
        cfg, settings, character, identity = self._settings()
        if identity != self.identity:
            self.apply_config()
        snapshot = self.snapshot()
        mono, now = self.monotonic(), self.clock()
        candidates = self.scheduler.candidates(snapshot, now, mono, cfg)
        if not snapshot.allowed or not cfg['enabled'] or not settings.enabled:
            if self.token or self.chat.busy:
                self.cancel()
            return
        if self.busy or self.unavailable == identity:
            return
        if self.last_mono is not None and mono-self.last_mono < cfg['min_interval_minutes']*60:
            return
        if category:
            candidates = [c for c in candidates if c.category == category]
        if not candidates:
            return
        policy = MemoryContext.from_config(self.config, '')
        provider = replace(settings.active_config, max_tokens=96, timeout=min(20, settings.active_config.timeout))
        style = style_context(self.config)
        def preflight():
            if not provider.api_key and not self.fake:
                provider.api_key = SecretStore().get(provider.api_key_ref)
            if not self.fake and (not provider.api_key or not provider.base_url or not provider.model):
                return {'unavailable': True}
            signature = hashlib.sha256((identity+provider.api_key).encode()).hexdigest()
            for candidate in candidates:
                token = self.state.reserve(candidate.event, candidate.category, now, cfg, signature)
                if token:
                    recent = self.state.recent()
                    builder = PromptBuilder(Path(__file__).resolve().parents[2]/'assets'/'characters')
                    role = builder.effective_system_prompt(settings, character)
                    messages = [{'role': 'system', 'content': role}, style_message(style), {'role': 'system', 'content':
                        '内部主动陪伴任务，不是用户发言。保持当前角色，温柔自然、稍俏皮。仅输出1至2句话，最多80字。'
                        '不要推测用户事实，不宣称监视用户，不创建日程，不要求回答。根据时段与主题动态写新话，不重复最近内容。'
                        +json.dumps({'local_time': now.strftime('%Y-%m-%d %H:%M'), 'topic': candidate.category,
                                    'recent_topics': provider_history_summary(recent)}, ensure_ascii=False)}]
                    window = self.state.request_window(token)
                    if window is None:
                        return {}
                    context = ReadOnlyMemory(policy, cfg['use_memory'] and candidate.category == 'care', window=window, clock=self.clock)
                    return dict(token=token, messages=messages, provider=provider, signature=signature,
                                context=context, category=candidate.category, cfg=cfg)
            return {}
        self._submit(preflight, self._ready)

    def _ready(self, result, generation):
        if not result:
            return
        if result.get('unavailable'):
            self.unavailable = self.identity
            self._status('未配置有效凭据；等待配置更改，不请求网络')
            return
        if 'token' not in result:
            return
        if generation != self.generation or self.closed or not self.snapshot().allowed or self._settings()[3] != self.identity or not result['context'].request_valid():
            self._submit(lambda: self.state.release(result['token']), lambda *_: None)
            return
        self.token = result['token']
        self.request = result
        self.context = result['context']
        self._start_request()

    def _start_request(self):
        self.failure = {}
        self.rid = self.chat.send(self.request['messages'], self.request['provider'], memory_context=self.context, output_limit=256)
        self.deadline.start()
        self._status('正在生成简短陪伴气泡')

    def _result(self, rid, text):
        if rid != getattr(self, 'rid', None) or not self.token:
            return
        self.deadline.stop()
        text = text.strip()
        token, context, cfg, category = self.token, self.context, self.request['cfg'], self.request['category']
        now = self.clock()
        def validate():
            if not text or len(text) > 80 or sensitive(text) or not context.valid():
                return 'discard'
            if repeats(text, self.state.recent(), now.timestamp(), cfg['avoid_semantic_repeats'], category):
                return 'retry' if self.state.retry_attempt(token, cfg, now) else 'discard'
            return 'show' if self.state.mark_presenting(token, now) else 'discard'
        self._submit(validate, lambda result, gen: self._validated(result, gen, text, now))

    def _validated(self, result, generation, text, now):
        if generation != self.generation or not self.token:
            return
        if self._settings()[3] != self.identity:
            self.cancel()
            return
        actual_now = self.clock()
        if actual_now.date() != now.date() or abs(actual_now.timestamp()-now.timestamp()) > 5 or not self.context.request_valid():
            self.cancel()
            return
        now = actual_now
        if result == 'retry' and self.snapshot().allowed and self._settings()[0]['enabled']:
            self.request['messages'] = [*self.request['messages'], {'role': 'system', 'content': '上一候选与近期台词重复；改用不同表达与适当主题，仍须遵守原任务。'}]
            self._start_request()
            return
        if result != 'show':
            self.cancel()
            return
        shown = False
        # Never carry an old role/provider/config result into its replacement.
        if self.snapshot().allowed and self._settings()[3] == self.identity:
            try:
                shown = self.present(text) is True
            except (RuntimeError, AttributeError):
                shown = False
        token, category = self.token, self.request['category']
        self.token = None
        receipt_time = self.clock()
        if shown:
            self.last_mono = self.monotonic()
            self.delivered.emit(text)
        self._submit(lambda: self.state.finish(token, text, sorted(classify(text, category)), receipt_time, shown),
                     lambda settled, gen: self._settled(settled, gen, shown))
        self._status('气泡已接受，等待结算' if shown else '窗口未接受气泡；不计成功次数')

    def _settled(self, settled, generation, shown):
        if self.closed or generation != self.generation:
            return
        self._status('已显示并结算' if shown and settled is True else
                     '展示结算未确认；保守占位' if shown else '窗口未接受气泡；不计成功次数')

    def _failure_info(self, rid, info):
        if rid == getattr(self, 'rid', None):
            self.failure = info

    def _error(self, rid, _private_error):
        if rid != getattr(self, 'rid', None) or not self.token:
            return
        self.deadline.stop()
        now, info, signature = self.clock(), self.failure, self.request['signature']
        if info.get('status') == 401:
            self.unavailable = self.identity  # Also fail closed if persisting backoff fails.
        self._submit(lambda: self.state.failure(info.get('status'), info.get('retry_after', 0), now, signature), lambda *_: None)
        self.cancel()
        self._status('模型暂不可用；已退避，不播放固定台词')

    def _timeout(self):
        self._error(getattr(self, 'rid', None), '')

    def cancel(self):
        self.generation += 1
        self.deadline.stop()
        self.chat.stop()
        token, self.token = self.token, None
        if token:
            self._submit(lambda: self.state.release(token), lambda *_: None)

    def close(self):
        if self.closed:
            return
        self.cancel()
        self.timer.stop()
        self.closed = True
        if self._manual_callback in ChatService._global_started_listeners:
            ChatService._global_started_listeners.remove(self._manual_callback)
        self.pool.shutdown(wait=False)
        if self.chat._workers:
            _LIVE.add(self)
            for worker in list(self.chat._workers):
                worker.finished.connect(self._release_pin, Qt.QueuedConnection)

    def _release_pin(self):
        if not any(w.isRunning() for w in self.chat._workers):
            _LIVE.discard(self)
