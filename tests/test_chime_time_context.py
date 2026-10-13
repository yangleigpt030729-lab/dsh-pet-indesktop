from datetime import datetime, timedelta
import pytest
from pet.voice_chime import normalize_chime_config, pick_quote, build_chime_sentence, build_bubble_sentence, cache_key

@pytest.mark.parametrize('hour,word', [(0,'夜'),(7,'早餐'),(10,'工作'),(12,'午'),(15,'午后'),(18,'晚餐'),(22,'夜')])
@pytest.mark.parametrize('english', [False,True])
def test_default_context_and_language(hour, word, english):
    cfg = normalize_chime_config({'voice_chime_voice': 'en-US-AriaNeural' if english else 'zh-CN-XiaoxiaoNeural'})
    now = datetime(2026,10,14,hour)
    quote = pick_quote(now,cfg)
    from pet.voice_chime_quotes import contextual_quotes
    assert quote in contextual_quotes(hour, english=english)
    assert quote in build_chime_sentence(now,cfg) and quote in build_bubble_sentence(now,cfg)
    assert quote == pick_quote(now,cfg)
    assert quote != pick_quote(now+timedelta(days=1),cfg)
    if english:
        assert not any('\u4e00' <= c <= '\u9fff' for c in build_chime_sentence(now,cfg))
    assert cache_key(build_chime_sentence(now,cfg),cfg) != cache_key(build_chime_sentence(now+timedelta(days=1),cfg),cfg)

@pytest.mark.parametrize('english',[False,True])
def test_custom_and_no_quote_override_context(english):
    cfg = normalize_chime_config({'voice_chime_voice':'en-US-AriaNeural' if english else 'zh-CN-XiaoxiaoNeural',
        'voice_chime_custom_quotes_en':'My own line.', 'voice_chime_custom_quotes_zh':'自己的台词。'})
    for hour in range(24):
        text = build_chime_sentence(datetime(2026,10,14,hour),cfg)
        assert ('My own line.' if english else '自己的台词。') in text
        cfg['show_quote']=False
        assert 'My own line.' not in build_chime_sentence(datetime(2026,10,14,hour),cfg)
        assert '自己的台词。' not in build_chime_sentence(datetime(2026,10,14,hour),cfg)
        cfg['show_quote']=True
