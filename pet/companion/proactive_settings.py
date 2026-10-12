"""Shared AI settings rows; immediate opt-in, merged with latest config."""
from PySide6.QtWidgets import QLabel, QMessageBox
from ..settings_widgets import SettingRow, SettingsSection, ToggleSwitch, BrowserSpinBox
from .proactive_config import normalize_config


class ProactiveSettings(SettingsSection):
    def __init__(self, config, parent=None):
        self.config = config
        self.controls = {}
        values = normalize_config(config.get('proactive_chat'))
        rows = []
        labels = [('enabled', '主动 AI 陪伴', '默认关闭。明确开启后可能调用付费模型；只显示文字气泡，不播语音。立即生效。'),
                  ('greetings', '自然问候', '按本地上午、下午、晚上选择合适时机。'),
                  ('water_reminders', '喝水提醒', '有持续活动时考虑提醒，同类主题冷却两小时。'),
                  ('break_reminders', '休息提醒', '持续活动一小时后考虑提醒；睡眠与离开时间不计入。'),
                  ('use_memory', '使用已授权记忆', '仅温和关心话题读取少量安全记录；还需启用长期记忆。'),
                  ('avoid_semantic_repeats', '避免相似主动台词', '本地文字与语义标签去重；不产生额外模型分类费用。')]
        for key, title, hint in labels:
            control = ToggleSwitch()
            control.setChecked(values[key])
            self.controls[key] = control
            rows.append(SettingRow('proactive_chat_'+key, title, hint, control))
        for key, title, hint, low, high in [
                ('daily_limit', '每日展示上限', '问候、喝水、休息、关心共用额度，最多10条，重启保留。', 0, 10),
                ('min_interval_minutes', '最短间隔（分钟）', '最少30分钟；间隔满足也不会强制发言。', 30, 180)]:
            control = BrowserSpinBox()
            control.setRange(low, high)
            control.setValue(values[key])
            self.controls[key] = control
            rows.append(SettingRow('proactive_chat_'+key, title, hint, control))
        status = QLabel('未启用时零主动请求。开启后等待合适时机；缺少凭据时不请求网络。')
        status.setWordWrap(True)
        rows.append(SettingRow('proactive_chat_status', '运行与费用', '每日请求硬上限为展示额度的两倍，每次最多96输出token；模型失败有界退避。默认全天可用，仍尊重锁屏、全屏和手动聊天。', status, stacked=True))
        reserved = ToggleSwitch()
        reserved.setChecked(values['scheduled_reminders'])
        reserved.setEnabled(False)
        rows.append(SettingRow('proactive_chat_scheduled_reminders', '日程增强（尚未实现）', 'NOT IMPLEMENTED：本轮仅保留P2-C配置意向；原待办行为保持原样。', reserved))
        super().__init__('主动 AI 陪伴', rows, parent)
        for key, control in self.controls.items():
            signal = control.toggled if isinstance(control, ToggleSwitch) else control.valueChanged
            signal.connect(lambda value, key=key: self._save(key, value))
        self._dependencies()

    def _dependencies(self):
        for key, control in self.controls.items():
            if key != 'enabled':
                control.setEnabled(self.controls['enabled'].isChecked())

    def _save(self, key, value):
        if key == 'enabled':
            from .proactive_policy import set_enabled
            set_enabled(self.config.path, value)
        self.config.reload()
        values = normalize_config(self.config.get('proactive_chat'))
        values[key] = value
        self.config.set('proactive_chat', values)
        if not self.config.save():
            QMessageBox.warning(self, '陪伴设置保存失败', '本次选择保留在当前进程；请检查用户目录权限并重试保存。')
        self._dependencies()
