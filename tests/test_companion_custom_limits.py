import json
from datetime import timedelta
import pytest
from pet.companion.proactive_config import normalize_config
from pet.companion.proactive_state import ProactiveState
from pet.config import Config
from tests.test_companion_proactive_state import START


@pytest.mark.parametrize('limit', [1, 10, 9999])
@pytest.mark.parametrize('interval', [1, 30, 99])
def test_limits_roundtrip_and_durable_last_slot(tmp_path, limit, interval):
    cfg = Config(base=tmp_path)
    cfg.set('proactive_chat', {'enabled': True, 'daily_limit': limit, 'min_interval_minutes': interval})
    cfg.save()
    values = Config(base=tmp_path).get('proactive_chat')
    assert values['daily_limit'] == limit and values['min_interval_minutes'] == interval
    state = ProactiveState(tmp_path/'state.db')
    with state.db() as db:
        db.execute('INSERT INTO days VALUES (?, ?,0,0)', (START.date().isoformat(), limit-1))
    token = state.reserve('last', 'new-topic', START, values, 'fake')
    assert token and state.mark_presenting(token, START)
    assert state.finish(token, '合成测试', [], START, True)
    assert state.stats(START.date().isoformat())['successes'] == limit
    assert not state.reserve('over', 'other', START+timedelta(minutes=interval), values, 'fake')


def test_one_minute_interval_and_more_than_ten_are_real_backend_settings(tmp_path):
    state = ProactiveState(tmp_path/'state.db')
    values = normalize_config({'enabled': True, 'daily_limit': 9999, 'min_interval_minutes': 1})
    for n in range(12):
        now = START+timedelta(minutes=n)
        token = state.reserve(str(n), 'unique'+str(n), now, values, 'fake')
        assert token and state.mark_presenting(token, now)
        assert state.finish(token, '合成测试'+str(n), [], now, True)
        assert not state.reserve('early'+str(n), 'early', now+timedelta(seconds=59), values, 'fake')
    assert state.stats(START.date().isoformat())['successes'] == 12


@pytest.mark.parametrize('raw,key,value', [({'daily_limit': 0}, 'daily_limit', 0),
                                         ({'min_interval_minutes': 180}, 'min_interval_minutes', 180)])
def test_old_quiet_preferences_are_paused_and_preserved(tmp_path, raw, key, value):
    cfg = Config(base=tmp_path)
    cfg.path.parent.mkdir(parents=True, exist_ok=True)
    cfg.path.write_text(json.dumps({'proactive_chat': {'enabled': True, **raw}}), encoding='utf-8')
    cfg = Config(base=tmp_path)
    values = cfg.get('proactive_chat')
    assert values['enabled'] is False
    assert values['legacy_ranges'][key] == value and values['range_review'] is True
    cfg.save()
    assert Config(base=tmp_path).get('proactive_chat') == values


def test_ui_numeric_ranges_and_placeholder_removal(tmp_path):
    from tests.test_companion_chat import wait
    from PySide6.QtWidgets import QApplication
    from pet.companion.proactive_settings import ProactiveSettings
    from pet.settings_widgets import SettingRow
    app = QApplication.instance() or QApplication([])
    cfg = Config(base=tmp_path)
    page = ProactiveSettings(cfg)
    try:
        assert page.controls['daily_limit'].minimum() == 1
        assert page.controls['daily_limit'].maximum() == 9999
        assert page.controls['min_interval_minutes'].minimum() == 1
        assert page.controls['min_interval_minutes'].maximum() == 99
        assert page.findChild(SettingRow, 'settingRow_proactive_chat_scheduled_reminders') is None
        page.controls['enabled'].setChecked(True)
        page.controls['daily_limit'].setValue(9999)
        page.controls['min_interval_minutes'].setValue(1)
        wait(app, lambda: Config(base=tmp_path).get('proactive_chat')['daily_limit'] == 9999)
        assert Config(base=tmp_path).get('proactive_chat')['min_interval_minutes'] == 1
    finally:
        page.deleteLater()
