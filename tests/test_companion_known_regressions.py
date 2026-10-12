from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication
from pet.agent_link import BaseAgentMonitor


def test_deleted_monitor_emission_stops_worker_without_runtime_error(tmp_path):
    app = QApplication.instance() or QApplication([])
    mon = BaseAgentMonitor('synthetic', tmp_path)
    signal = mon.activity
    mon.deleteLater()
    QCoreApplication.sendPostedEvents(mon, QEvent.Type.DeferredDelete)
    mon._emit(signal, ('synthetic', 'task', 1))
    assert mon._worker_stop.is_set()


def test_interaction_target_rejects_destroyed_overlay_surface(tmp_path):
    from pet.config import Config
    from pet.app import PetInstance
    from pet.companion.interaction_runtime import Target
    from tests.test_settings_process_isolation import _bare_shell
    from tests.test_companion_settings_entry import overlay_for
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    shell = _bare_shell(cfg)
    shell.instance = PetInstance(shell, cfg)
    host = overlay_for(shell, cfg)
    host.overlay.show()
    target = Target(host, host.sprite)
    try:
        assert target.valid()
        host.overlay.deleteLater()
        QCoreApplication.sendPostedEvents(host.overlay, QEvent.Type.DeferredDelete)
        assert not target.valid()
        assert not target.present('合成迟到结果')
    finally:
        host.stop()


def test_completed_chat_workers_release_native_objects_even_if_observed():
    import shiboken6
    from pet.chat.service import ChatService
    from pet.chat.models import ProviderConfig
    from tests.test_companion_chat import wait
    from tests.test_companion_proactive_service import FakeProvider
    app = QApplication.instance() or QApplication([])
    service = ChatService(FakeProvider(), notify_global=False)
    observed = []
    try:
        for _ in range(10):
            service.send([{'role': 'system', 'content': 'synthetic'}], ProviderConfig('synthetic'))
            observed.append(service._worker)
            def disposed():
                if shiboken6.isValid(observed[-1]):
                    QCoreApplication.sendPostedEvents(observed[-1], QEvent.Type.DeferredDelete)
                return not service._workers and not shiboken6.isValid(observed[-1])
            # Collection removal and deleteLater are separate queued deliveries.
            wait(app, disposed)
        assert all(not shiboken6.isValid(w) for w in observed)
    finally:
        service.shutdown()
