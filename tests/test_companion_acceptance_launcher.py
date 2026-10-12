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
