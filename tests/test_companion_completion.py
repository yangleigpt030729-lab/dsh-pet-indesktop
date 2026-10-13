"""Real SSE provider/Qt worker; synthetic network response only."""
import json
import pytest
from pet.chat.providers import OpenAICompatibleProvider
from tests.test_companion_interactions import setup
from tests.test_companion_chat import wait

class Response:
    def __init__(self, chunks):
        self.chunks = iter(chunks)
    def read(self, _n):
        item = next(self.chunks, b'')
        if isinstance(item, Exception):
            raise item
        return item
    def close(self):
        pass

def event(text='', reason=None):
    return ('data: '+json.dumps({'choices': [{'delta': {'content': text}, 'finish_reason': reason}]})+'\n\n').encode()

@pytest.mark.parametrize('ending,success', [
    ([event(reason='stop')], True),
    ([event(reason='length'), b'data: [DONE]\n\n'], False),
    ([b'data: [DONE]\n\n'], True),
    ([], False),
    ([OSError('synthetic network interruption')], False),
])
def test_interaction_accepts_complete_stream_only(tmp_path, monkeypatch, ending, success):
    expected = '鱼鳍开心地翘起来啦，谢谢你温柔地摸摸我。'
    calls = []
    def urlopen(request, **kwargs):
        calls.append(json.loads(request.data))
        return Response([event(expected), *ending])
    monkeypatch.setattr('urllib.request.urlopen', urlopen)
    app, cfg, target, service = setup(tmp_path, OpenAICompatibleProvider())
    settings = cfg.chat_settings()
    settings.active_config.api_key = 'synthetic-not-a-secret'
    cfg.set_chat_settings(settings)
    try:
        assert service.request('head', target)
        wait(app, lambda: not service.busy)
        assert len(calls) == 1 and calls[0]['max_tokens'] == 256
        assert len(target.texts) == 1
        assert (target.texts[0] == expected) is success
    finally:
        service.close()

@pytest.mark.parametrize('size',[12,79,80])
def test_head_budget_stays_local_and_complete_near_limit_is_preserved(tmp_path,size):
    from tests.test_companion_proactive_service import FakeProvider
    from pet.chat.models import ProviderConfig
    sentence='好'*(size-1)+'。'
    provider=FakeProvider([sentence])
    app,cfg,target,service=setup(tmp_path,provider)
    original=cfg.chat_settings().active_config.max_tokens
    try:
        service.request('head',target)
        wait(app,lambda:not service.busy)
        assert target.texts==[sentence] and provider.calls[0][1].max_tokens==256
        assert cfg.chat_settings().active_config.max_tokens==original
        assert ProviderConfig('default').max_tokens!=256
    finally:service.close()
