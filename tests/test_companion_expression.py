import json
import threading
import pytest
from pet.config import Config
from tests.test_companion_proactive_service import FakeProvider, setup as proactive_setup
from tests.test_companion_interactions import setup
from tests.test_companion_chat import wait


@pytest.mark.parametrize('mode', ['legacy', 'whale_maid', 'custom'])
@pytest.mark.parametrize('kind', ['greeting', 'drink', 'break', 'care', 'head', 'feeding'])
def test_actual_provider_prompt_keeps_role_and_adapts_style_without_private_phrases(tmp_path, mode, kind):
    provider = FakeProvider(['今天也一起慢慢来。'])
    if kind in ('head', 'feeding'):
        app, cfg, target, service = setup(tmp_path, provider)
    else:
        app, cfg, service, bubbles = proactive_setup(tmp_path, provider)
    cfg.set('dialogue_mode', mode)
    cfg.set('dialogue_phrases', {'global': {'start': ['PRIVATE-CUSTOM-DO-NOT-UPLOAD']}})
    settings = cfg.chat_settings()
    settings.default_system_prompt = 'ROLE-PRESERVED'
    cfg.set_chat_settings(settings)
    cfg.set('character', 'synthetic-role-no-manifest')
    cfg.save()
    try:
        if kind in ('head', 'feeding'):
            service.request(kind, target)
        else:
            from pet.companion.proactive_schedule import Candidate
            service.scheduler.candidates = lambda *a: [Candidate('synthetic:'+kind, kind)]
            service.tick()
        wait(app, lambda: not service.busy)
        assert provider.calls
        messages = provider.calls[0][0]
        assert messages[0]['content'] == 'ROLE-PRESERVED'
        payload = json.dumps(messages, ensure_ascii=False)
        assert 'PRIVATE-CUSTOM' not in payload
        style = next(m for m in messages if 'expression_style' in m['content'])
        assert f'"mode": "{mode}"' in style['content']
        assert ('主人' in style['content']) == (mode == 'whale_maid')
        assert messages[-1] is not style and '不是用户' in messages[-1]['content']
    finally:
        service.close()


@pytest.mark.parametrize('kind', ['head', 'feeding'])
def test_style_change_discards_inflight_interaction_and_local_fallback_matches_builtin(tmp_path, kind):
    barrier = threading.Event()
    provider = FakeProvider(['旧风格回复。'], barrier=barrier)
    app, cfg, target, service = setup(tmp_path, provider)
    try:
        service.request(kind, target)
        wait(app, lambda: bool(provider.calls))
        cfg.set('dialogue_mode', 'whale_maid')  # No disk watcher needed for in-process change.
        barrier.set()
        wait(app, lambda: not service.busy)
        assert target.texts == []
        service.backoff = service.clock()+120
        service.request(kind, target)
        wait(app, lambda: not service.busy)
        assert '主人' in target.texts[0]
    finally:
        barrier.set()
        service.close()


def test_unsaved_style_change_cancels_inflight_proactive(tmp_path):
    barrier = threading.Event()
    provider = FakeProvider(['旧风格问候。'], barrier=barrier)
    app, cfg, service, bubbles = proactive_setup(tmp_path, provider)
    try:
        service.tick()
        wait(app, lambda: bool(provider.calls))
        cfg.set('dialogue_mode', 'whale_maid')
        barrier.set()
        wait(app, lambda: not service.busy)
        assert bubbles == []
    finally:
        barrier.set()
        service.close()
