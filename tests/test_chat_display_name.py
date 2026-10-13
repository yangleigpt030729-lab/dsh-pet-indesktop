import pytest
from tests.test_chat_persona_priority import chat_window
from tests.test_companion_proactive_service import FakeProvider
from tests.test_companion_chat import wait

@pytest.mark.parametrize('module', ['pet.chat.legacy_widgets', 'pet.chat.widgets'])
def test_alias_updates_open_window_without_changing_session(tmp_path, monkeypatch, module):
    app, cfg, window = chat_window(tmp_path, module, FakeProvider(['unused']), monkeypatch)
    original = window.session.session_id
    try:
        cfg.set_character_alias('shenshen', '大肥鱼')
        wait(app, lambda: window.character_name == '大肥鱼')
        assert window.character_id == 'shenshen' and window.session.session_id == original
        window.close()
        window.show()
        assert window.character_name == '大肥鱼'
        cfg.set_character_alias('shenshen', '')
        wait(app, lambda: window.character_name == cfg.character_display_name('shenshen'))
        cfg.set_character_alias('other', '小鱼')
        window.switch_character('other')
        assert window.character_name == '小鱼' and window.character_id == 'other'
    finally:
        window.service.shutdown()
        window.close()
