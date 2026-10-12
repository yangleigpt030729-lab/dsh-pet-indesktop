"""Unique immediate opt-ins inside the existing AI capability domain."""
from PySide6.QtWidgets import QMessageBox
from ..settings_widgets import SettingsSection, SettingRow, ToggleSwitch
from .interaction_config import normalize_config
from .proactive_policy import set_enabled


class InteractionSettings(SettingsSection):
    def __init__(self, config, parent=None):
        self.config = config
        values = normalize_config(config.get('companion_interaction'))
        self.controls = {}
        rows = []
        for key, title, hint in [
            ('head_touch_enabled', '摸头 AI', '默认关闭。单击可见头部核心才调用模型；身体点击、拖拽保留原样。同宠冷却10秒，单次最多96输出token，可能额外计费。只显示文字；已授权记忆可少量引用，不保存摸头为用户事实。'),
            ('feeding_enabled', 'AI 投喂反馈', '默认关闭。只发送类别、数量和大小区间；不发送文件名、路径或内容，不假装看过文件。连续投喂合并，同宠冷却20秒，模型请求可能额外计费。原吃文件、统计和独立解读授权保持有效。')]:
            control = ToggleSwitch()
            control.setChecked(values[key])
            self.controls[key] = control
            rows.append(SettingRow('companion_'+key, title, hint, control))
        super().__init__('点击与投喂 AI', rows, parent)
        for key, control in self.controls.items():
            control.toggled.connect(lambda value, key=key: self._save(key, value))

    def _save(self, key, value):
        set_enabled(self.config.path, value, feature=key)
        self.config.reload()
        values = normalize_config(self.config.get('companion_interaction'))
        values[key] = value
        self.config.set('companion_interaction', values)
        if not self.config.save():
            QMessageBox.warning(self, '交互设置暂未保存', '选择在当前进程生效。请检查用户目录权限并重新保存；重启前请确认保存成功。')
