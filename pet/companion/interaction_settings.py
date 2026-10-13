"""Unique immediate opt-ins reused by their owning settings domains."""
from PySide6.QtWidgets import QMessageBox
from ..settings_widgets import SettingsSection, SettingRow, ToggleSwitch
from .interaction_config import normalize_config
from .proactive_policy import set_enabled

_FIELDS = {
    'head_touch_enabled': ('摸头 AI', '默认关闭。单击可见头部核心才调用模型，身体点击与拖拽保留。冷却10秒、最多96输出token，可能计费；已授权记忆可少量引用，不保存为用户事实。文字显示成功后可由下方共享朗读开关朗读。'),
    'feeding_enabled': ('AI 投喂反馈', '默认关闭。只发送类别、数量和大小区间，不发送文件名、路径或内容，不假装看过文件。连续投喂合并，冷却20秒，可能计费。只显示文字，原统计和独立解读授权保持有效。'),
}


def setting_row(config, key, changed=None):
    control = ToggleSwitch()
    control.setChecked(normalize_config(config.get('companion_interaction'))[key])
    title, hint = _FIELDS[key]
    row = SettingRow('companion_'+key, title, hint, control)
    def save(value):
        set_enabled(config.path, value, feature=key)
        config.reload()
        values = normalize_config(config.get('companion_interaction'))
        values[key] = value
        config.set('companion_interaction', values)
        if not config.save():
            QMessageBox.warning(row, '交互设置暂未保存', '选择在当前进程生效。请检查用户目录权限并重新保存；重启前请确认保存成功。')
        if changed:
            changed(value)
    control.toggled.connect(save)
    return row, control


class InteractionSettings(SettingsSection):
    def __init__(self, config, parent=None, *, keys=('head_touch_enabled', 'feeding_enabled')):
        self.config, self.controls = config, {}
        rows = []
        for key in keys:
            row, control = setting_row(config, key)
            rows.append(row)
            self.controls[key] = control
        super().__init__('AI 投喂反馈' if keys == ('feeding_enabled',) else '点击与投喂 AI', rows, parent)
