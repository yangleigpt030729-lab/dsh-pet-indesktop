from datetime import datetime, timedelta
import pytest
from pet.chat.providers import ProviderError, retry_after_seconds
from tests.test_companion_proactive_service import FakeProvider, setup
from tests.test_companion_chat import wait


@pytest.mark.parametrize('failure', [ProviderError('synthetic-secret-value', 401), ProviderError('synthetic-secret-value', 429, 3600), ConnectionError('synthetic-secret-value'), TimeoutError('synthetic-secret-value'), ValueError('synthetic-secret-value'), '', '鱼'*81, '鱼'*300])
def test_failures_no_display_no_leak_no_infinite_attempts(tmp_path, failure, caplog):
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider([failure]))
    s.tick()
    wait(app, lambda: not s.busy)
    for _ in range(4):
        s.tick()
        wait(app, lambda: not s.busy)
    stats = s.state.stats(datetime.now().astimezone().date().isoformat())
    assert not bubbles and stats['successes'] == 0
    assert stats['attempts'] <= 5
    assert 'synthetic-secret-value' not in caplog.text + s.status
    s.close()


def test_401_persists_until_configuration_changes(tmp_path):
    app, cfg, s, bubbles = setup(tmp_path, FakeProvider([ProviderError('private', 401), '窗外有风，今天也慢慢来呀。']))
    now = [datetime.now().astimezone()]
    s.clock = lambda: now[0]
    s.tick()
    wait(app, lambda: not s.busy)
    now[0] += timedelta(days=1)
    s.tick()
    wait(app, lambda: not s.busy)
    assert len(s.chat.provider.calls) == 1
    settings = cfg.chat_settings()
    settings.active_config.model = 'changed-fake-model'
    cfg.set_chat_settings(settings)
    cfg.save()
    s.tick()
    wait(app, lambda: not s.busy)
    assert len(s.chat.provider.calls) == 2 and len(bubbles) == 1
    s.close()


def test_retry_after_parser_bounds():
    assert retry_after_seconds('120') == 120
    assert retry_after_seconds('99999999') == 86400
    assert retry_after_seconds('-1') == 0
    assert retry_after_seconds('garbage') == 0
