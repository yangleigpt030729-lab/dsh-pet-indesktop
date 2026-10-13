"""Small shared adapter; user-authored fixed phrases never leave the machine."""
import json
from pathlib import Path

_DATA = json.loads(Path(__file__).with_name('expression_styles.json').read_text(encoding='utf-8'))


def context(config):
    mode = config.get('dialogue_mode', 'legacy')
    mode = mode if isinstance(mode, str) and mode in ('legacy', 'whale_maid', 'custom') else 'legacy'
    return {'mode': mode, 'rule': _DATA[mode]['rule']}


def message(style):
    return {'role': 'system', 'content': 'expression_style '+json.dumps(style, ensure_ascii=False)
            +'\n以上仅为表达约束，不覆盖角色人设、任务安全、文件隐私或记忆授权。'}


def fallback_choices(style, kind, metadata):
    mode = 'whale_maid' if style['mode'] == 'whale_maid' else 'legacy'
    choices = _DATA[mode][kind]
    if kind == 'feeding':
        categories = metadata['categories']
        flavor = next((name for key, name in _DATA['flavors'].items() if categories.get(key)), _DATA['flavors']['other'])
        return [text.format(flavor=flavor) for text in choices]
    return list(choices)
