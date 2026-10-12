from datetime import datetime, timedelta, timezone
from pet.companion.proactive_config import normalize_config
from pet.companion.proactive_schedule import Scheduler, Snapshot
from pet.companion.proactive_repeat import classify, repeats


def test_semantic_multitag_and_punctuation():
    assert {'greeting', 'drink'} <= classify('早呀！也别忘了补充水分。', 'greeting')
    assert 'break' in classify('久坐了，起来伸个懒腰', 'care')
    assert repeats('记得喝水哦!', [{'text': '记得喝水哦。', 'tags': '["drink"]', 'utc': 1}], 9000, True)
    assert repeats('今天也要补充水分呀', [{'text': '记得喝水哦', 'tags': '["drink"]', 'utc': 1}], 1000, True)
    assert not repeats('窗外的云好像一条鱼', [{'text': '记得喝水哦', 'tags': '["drink"]', 'utc': 1}], 1000, True)


def test_scheduler_gates_sleep_and_activity():
    cfg = normalize_config({'enabled': True})
    s = Scheduler()
    now = datetime(2026, 10, 12, 8, tzinfo=timezone.utc)
    assert s.candidates(Snapshot(visible=False), now, 0, cfg) == []
    assert s.candidates(Snapshot(typing=True), now, 0, cfg) == []
    assert s.candidates(Snapshot(), now, 0, cfg)[0].category == 'greeting'
    for n in range(1, 122):
        items = s.candidates(Snapshot(), now+timedelta(seconds=n*30), n*30, cfg)
    assert 'break' in [c.category for c in items]
    s.candidates(Snapshot(), now+timedelta(hours=9), 9*3600, cfg)
    assert s.activity == 0  # sleep/absence is not continuous work
    assert s.candidates(Snapshot(suspended=True), now, 10*3600, cfg) == []
    cfg['enabled'] = False
    assert s.candidates(Snapshot(), now, 10*3600, cfg) == []
