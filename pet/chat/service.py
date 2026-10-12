from __future__ import annotations
import threading, uuid
from typing import Any
from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import QApplication
from .models import ProviderConfig
from .providers import OpenAICompatibleProvider
class _Worker(QThread):
    delta_received=Signal(str); completed=Signal(str); failed=Signal(str); stopped_by_user=Signal()
    failure_info = Signal(object)
    def __init__(self,provider,messages,config,cancel,memory_context=None):
        super().__init__()
        self.provider=provider; self.messages=messages; self.config=config; self.cancel=cancel; self.parts=[]
        self._responses = []
        self.memory_context = memory_context
        self.output_limit = None
        self.nonblocking_cancel = False
        self.safe_errors = False
        self._close_thread = None
    def cancel_response(self):
        self.cancel.set()
        if self.nonblocking_cancel:
            if self._close_thread is None and self._responses:
                responses = list(self._responses)
                def close_responses():
                    for response in responses:
                        try: response.close()
                        except Exception: pass
                self._close_thread = threading.Thread(target=close_responses, daemon=True, name='pet-chat-cancel')
                self._close_thread.start()
            return
        for resp in list(self._responses):
            try: resp.close()
            except Exception: pass
    def run(self):
        try:
            messages, memory_token = self.messages, None
            if self.memory_context is not None:
                messages, memory_token = self.memory_context.prepare(messages)
            if self.cancel.is_set():
                self.stopped_by_user.emit()
                return
            stream_kwargs = {}
            import inspect
            sig = inspect.signature(self.provider.stream)
            if 'response_holder' in sig.parameters:
                stream_kwargs['response_holder'] = self._responses
            for text in self.provider.stream(messages,self.config,self.cancel,**stream_kwargs):
                if self.cancel.is_set(): self.stopped_by_user.emit(); return
                self.parts.append(text)
                if self.output_limit is not None and sum(map(len, self.parts)) > self.output_limit:
                    raise ValueError('output limit exceeded')
                self.delta_received.emit(text)
            if self.cancel.is_set(): self.stopped_by_user.emit()
            else:
                result = ''.join(self.parts)
                if result.strip():
                    if self.memory_context is not None and not self.cancel.is_set():
                        self.memory_context.completed(memory_token)
                    if self.cancel.is_set():
                        self.stopped_by_user.emit()
                        return
                    self.completed.emit(result)
                else:
                    self.failed.emit('模型未返回任何内容，请稍后重试或检查模型配置。')
        except Exception as exc:
            if not self.cancel.is_set():
                self.failure_info.emit({'status': getattr(exc, 'status', None), 'retry_after': getattr(exc, 'retry_after', 0)})
            self.stopped_by_user.emit() if self.cancel.is_set() else self.failed.emit('模型请求失败' if self.safe_errors else str(exc))
class ChatService(QObject):
    started=Signal(str); delta=Signal(str,str); finished=Signal(str,str); error=Signal(str,str); stopped=Signal(str)
    # 进程级「回复完成」订阅（灵动岛事件动效等）：AppShell 注册一次，
    # 回调总在 GUI 线程执行（worker→本对象的链路全是 QueuedConnection）。
    _global_finished_listeners: list = []
    _global_started_listeners: list = []
    failure_info = Signal(str, object)

    @classmethod
    def register_global_finished(cls, callback):
        if callback not in cls._global_finished_listeners:
            cls._global_finished_listeners.append(callback)

    @classmethod
    def unregister_global_finished(cls, callback):
        if callback in cls._global_finished_listeners:
            cls._global_finished_listeners.remove(callback)

    def __init__(self,provider=None,parent=None,*,notify_global=True):
        super().__init__(parent); self.provider=provider or OpenAICompatibleProvider(); self._request_id=None; self._cancel=None; self._worker=None; self._workers=set()
        self.notify_global = notify_global
        # 退出时先取消并短等在飞 worker，避免 QThread 运行中被销毁导致崩溃
        app = QApplication.instance()
        if app is not None and notify_global:
            app.aboutToQuit.connect(self.shutdown)

    def shutdown(self) -> bool:
        # QThread 并非 daemon 线程，若在运行中被 Python GC 丢弃会触发 'QThread: Destroyed while running' 崩溃。
        # 因此取消并有界等待后，超时未退出的 worker 仍保留在 self._workers 集合中（不强行 clear/置空），
        # 等其 run() 结束后由 finished 信号自行 discard 回收引用。
        self.stop()
        for worker in list(self._workers):
            if hasattr(worker, "cancel_response") and callable(worker.cancel_response):
                try: worker.cancel_response()
                except Exception: pass
            elif hasattr(worker, "cancel") and worker.cancel is not None:
                worker.cancel.set()
            if worker.isRunning():
                worker.wait(1500)
        # 返回 True 表示全部退出，False 表示仍有 worker 在运行（供调用方参考）
        return not any(worker.isRunning() for worker in self._workers)
    @property
    def busy(self): return self._worker is not None and self._worker.isRunning()
    def send(self,messages:list[dict[str,Any]],config:ProviderConfig,request_id=None,*,memory_context=None,output_limit=None):
        self.stop(); rid=request_id or uuid.uuid4().hex; cancel=threading.Event(); worker=_Worker(self.provider,messages,config,cancel,memory_context); self._request_id=rid; self._cancel=cancel; self._worker=worker
        self._workers.add(worker)
        worker.output_limit = output_limit
        worker.nonblocking_cancel = not self.notify_global
        worker.safe_errors = not self.notify_global
        worker.failure_info.connect(lambda info,rid=rid:self.failure_info.emit(rid, info) if self._current(rid) else None, Qt.QueuedConnection)
        # 全部显式 QueuedConnection：worker 线程 emit 的信号若直连 lambda
        # 会在 worker 线程执行 _delta/_cleanup 等，与 GUI 线程的 busy()/
        # _request_id 读写构成数据竞态。队列投递保证回调只在 GUI 线程跑。
        worker.delta_received.connect(lambda text,rid=rid:self._delta(rid,text), Qt.QueuedConnection)
        worker.completed.connect(lambda text,rid=rid:self._finished(rid,text), Qt.QueuedConnection)
        worker.failed.connect(lambda text,rid=rid:self._error(rid,text), Qt.QueuedConnection)
        worker.stopped_by_user.connect(lambda rid=rid:self._stopped(rid), Qt.QueuedConnection)
        worker.finished.connect(lambda rid=rid:self._cleanup(rid), Qt.QueuedConnection)
        worker.finished.connect(lambda w=worker: self._workers.discard(w), Qt.QueuedConnection)
        if self.notify_global:
            for callback in list(type(self)._global_started_listeners):
                try: callback()
                except Exception: pass
        self.started.emit(rid); worker.start(); return rid
    def stop(self):
        if self._worker is not None:
            if hasattr(self._worker, "cancel_response") and callable(self._worker.cancel_response):
                try: self._worker.cancel_response()
                except Exception: pass
            elif hasattr(self._worker, "cancel") and self._worker.cancel is not None:
                self._worker.cancel.set()
        elif self._cancel is not None:
            self._cancel.set()
    def _current(self,rid): return rid==self._request_id
    def _delta(self,rid,text):
        if self._current(rid): self.delta.emit(rid,text)
    def _finished(self,rid,text):
        if self._current(rid):
            self.finished.emit(rid,text)
            for cb in list(type(self)._global_finished_listeners) if self.notify_global else []:
                try: cb(text)
                except Exception: pass
    def _error(self,rid,text):
        if self._current(rid): self.error.emit(rid,text)
    def _stopped(self,rid):
        if self._current(rid): self.stopped.emit(rid)
    def _cleanup(self,rid):
        if self._current(rid): self._worker=None; self._cancel=None
