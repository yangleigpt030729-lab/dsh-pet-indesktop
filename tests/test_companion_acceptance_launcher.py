from pathlib import Path
import pytest
from scripts.run_companion_acceptance import configure
from pet.config import Config


def test_test_configuration_has_distinct_keyref_and_owns_settings(tmp_path):
    cfg = configure(tmp_path/'isolated')
    provider = cfg.chat_settings().active_config
    assert provider.api_key_ref.startswith('provider/acceptance-')
    assert cfg.chat_settings().active_provider == provider.provider_id
    assert not cfg.get('settings_process_isolation')
    assert cfg.get('proactive_chat')['enabled'] is False
    cfg.save()
    assert configure(tmp_path/'isolated').chat_settings().active_config.api_key_ref == provider.api_key_ref


def test_acceptance_data_cannot_be_inside_source():
    root = Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError):
        configure(root/'private-acceptance-data')


def test_fake_provider_never_reads_system_credentials(tmp_path, monkeypatch):
    from pet.chat.models import SecretStore
    from tests.test_companion_proactive_service import FakeProvider, setup
    from tests.test_companion_chat import wait
    def forbidden(*a):
        pytest.fail('Fake Provider read real keyring')
    monkeypatch.setattr(SecretStore, 'get', forbidden)
    app, cfg, service, bubbles = setup(tmp_path, FakeProvider())
    service.tick()
    wait(app, lambda: not service.busy)
    assert len(bubbles) == 1
    service.close()


@pytest.fixture
def installed_fake(monkeypatch):
    import urllib.request
    from pet.chat import providers
    from pet.chat.models import SecretStore
    from pet.chat.service import ChatService
    from pet.companion.proactive_service import ProactiveService
    from scripts.run_companion_acceptance import install_fake_chat
    # Restore the process-only launcher modifications after this test.
    for owner, name in [(ChatService, '__init__'), (ProactiveService, '__init__'),
                        (SecretStore, 'get'), (SecretStore, 'set'),
                        (providers, 'test_connection'), (urllib.request, 'urlopen')]:
        monkeypatch.setattr(owner, name, getattr(owner, name))
    install_fake_chat()
    return install_fake_chat


def test_default_launcher_fake_reaches_real_qt_bubble_without_key(tmp_path, monkeypatch, installed_fake):
    from datetime import datetime
    from pet.chat.models import SecretStore, ProviderConfig
    from pet.chat.service import ChatService
    from pet.companion import proactive_runtime
    from pet import vision
    from tests.test_companion_chat import wait
    from tests.test_companion_settings_entry import overlay_for
    from tests.test_settings_process_isolation import _bare_shell
    from pet.app import PetInstance
    from PySide6.QtWidgets import QApplication
    import urllib.request
    app = QApplication.instance() or QApplication([])
    cfg = configure(tmp_path/'acceptance')
    cfg.set('proactive_chat', {'enabled': True})
    cfg.save()
    shell = _bare_shell(cfg)
    shell.enable_chat = True
    shell.instance = PetInstance(shell, cfg)
    shell._instances = [shell.instance]
    shell._overlay_shell = overlay_for(shell, cfg)
    shell._overlay_shell.overlay.show()
    monkeypatch.setattr(vision, 'get_system_idle_seconds', lambda: 0)
    accesses = []
    monkeypatch.setattr(SecretStore, 'get', lambda *a: accesses.append(a) or '')
    def forbidden(*a, **k):
        pytest.fail('Fake companion attempted real network/capture')
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr(vision, 'capture_screen_bytes', forbidden)
    monkeypatch.setattr(vision, 'capture_window_rect', forbidden)
    monkeypatch.setattr(type(shell), 'speak_self_talk', forbidden)
    from PySide6.QtMultimedia import QCamera, QAudioSource
    monkeypatch.setattr(QCamera, 'start', forbidden)
    monkeypatch.setattr(QAudioSource, 'start', forbidden)
    global_results = []
    ChatService.register_global_finished(global_results.append)
    service = None
    manual = ChatService()
    manual_results = []
    manual.finished.connect(lambda rid, text: manual_results.append(text))
    try:
        proactive_runtime.sync(shell)  # Exactly the normal AppShell constructor seam.
        service = shell.companion_service
        shown = []
        service.delivered.connect(shown.append)
        service.tick()
        wait(app, lambda: not service.busy)
        assert len(shown) == 1, service.status
        assert service.fake and '合成测试' in shown[0]
        bubble = shell._overlay_shell._speech_bubble
        assert bubble.isVisible() and bubble.text_was_presented(shown[0], after=0)
        assert accesses == [] and global_results == []
        assert service.chat.provider is not manual.provider
        assert service.state.stats(datetime.now().astimezone().date().isoformat())['successes'] == 1
        service.tick()
        wait(app, lambda: not service.busy)
        assert len(shown) == 1  # The launcher doesn't bypass the 30-minute gap.
        manual.send([{'role': 'user', 'content': '手动聊天测试'}], ProviderConfig('acceptance'))
        wait(app, lambda: manual_results and not manual._workers)
        assert len(manual_results) == len(global_results) == 1
        assert len(shown) == 1
        assert not (cfg.dir/'companion_memory.sqlite3').exists()
        assert not list(cfg.dir.glob('*sessions*'))
    finally:
        if service:
            service.close()
        manual.shutdown()
        shell._overlay_shell.stop()
        shell._overlay_shell.overlay.close()
        ChatService.unregister_global_finished(global_results.append)


def test_fake_launcher_disables_network_and_key_store(installed_fake, monkeypatch):
    import urllib.request
    import keyring
    from pet.chat.models import SecretStore
    def forbidden(*a, **k):
        pytest.fail('Real credential backend used')
    monkeypatch.setattr(keyring, 'get_password', forbidden)
    monkeypatch.setattr(keyring, 'set_password', forbidden)
    assert SecretStore.get('test') == ''
    assert SecretStore.set('test', 'synthetic') is False
    with pytest.raises(OSError, match='disables urllib'):
        urllib.request.urlopen('https://api.deepseek.com')


def test_fake_install_is_idempotent_and_discards_explicit_live_provider(installed_fake):
    from pet.chat.service import ChatService
    from pet.chat.providers import OpenAICompatibleProvider
    from pet.companion.proactive_service import ProactiveService
    original_chat, original_proactive = ChatService.__init__, ProactiveService.__init__
    installed_fake()
    assert ChatService.__init__ is original_chat
    assert ProactiveService.__init__ is original_proactive
    a, b = ChatService(OpenAICompatibleProvider()), ChatService()
    assert type(a.provider).__name__ == type(b.provider).__name__ == 'FakeProvider'
    assert a.provider is not b.provider
    a.shutdown()
    b.shutdown()


@pytest.mark.parametrize('topology', ['legacy', 'overlay'])
def test_unmodified_fake_launcher_displays_bubble_in_real_app_process(tmp_path, topology):
    import os
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'PET_RENDER_TOPOLOGY': topology,
           'PET_FRAMESEQ': '0', 'PYTHONUTF8': '1'}
    result = subprocess.run([sys.executable, '-X', 'utf8', 'scripts/run_companion_acceptance.py',
                             '--data-dir', str(tmp_path/'isolated'), '--auto-close-seconds', '8'],
                            cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count('FAKE: synthetic proactive bubble displayed') == 1, result.stdout + result.stderr
    from pet.companion.proactive_state import ProactiveState
    from datetime import datetime
    cfg = Config(base=tmp_path/'isolated')
    assert ProactiveState(cfg.dir/'companion_proactive.sqlite3').stats(
        datetime.now().astimezone().date().isoformat())['successes'] == 1
    assert not (cfg.dir/'companion_memory.sqlite3').exists()
    assert not list(cfg.dir.glob('*sessions*'))
