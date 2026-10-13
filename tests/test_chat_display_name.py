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


def test_role_rename_still_saves_when_optional_chat_package_is_absent(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    script = '''
import importlib.abc,json,sys
from pathlib import Path
from pet.config import Config
cfg=Config(base=Path(sys.argv[1]))
class NoChat(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,*args):
        if fullname=='pet.chat' or fullname.startswith('pet.chat.'):
            raise ModuleNotFoundError('synthetic no-chat build')
for name in list(sys.modules):
    if name=='pet.chat' or name.startswith('pet.chat.'):
        del sys.modules[name]
sys.meta_path.insert(0,NoChat())
cfg.set_character_alias('shenshen','大肥鱼')
assert json.loads(cfg.path.read_text(encoding='utf-8'))['character_aliases']['shenshen']=='大肥鱼'
assert not any(name=='pet.chat' or name.startswith('pet.chat.') for name in sys.modules)
'''
    result=subprocess.run([sys.executable,'-X','utf8','-c',script,str(tmp_path/'no-chat')],
                          cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
