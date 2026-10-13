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
        labels = [('enabled', '主动 AI 陪伴', '默认关闭。明确开启后可能调用付费模型；朗读由独立的主动陪伴朗读开关控制。立即生效。'),
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
                ('daily_limit', '每日展示上限', '1～9999条/天，默认10条；普通问候共用额度，重启保留，不保证用满。高额度可能增加DeepSeek费用。', 1, 9999),
                ('min_interval_minutes', '最短间隔（分钟）', '1～99分钟，默认30；短间隔可能增加费用，满足间隔也不强制发言。', 1, 99)]:
            control = BrowserSpinBox()
            control.setRange(low, high)
            control.setValue(values[key])
            self.controls[key] = control
            rows.append(SettingRow('proactive_chat_'+key, title, hint, control))
        self.speech_control = ToggleSwitch()
        self.speech_control.setChecked(bool(config.get('proactive_bubble_speak_enabled', False)))
        rows.append(SettingRow('proactive_chat_speak', '主动陪伴朗读',
            '默认关闭。独立控制已展示的主动问候、喝水/休息/关怀、待办及自动识屏AI回复。识屏只需其自身功能开关。开启即同意待播报文字（可能含私人待办或屏幕信息）发送到微软在线语音合成服务；进度、统计和仅桌面通知无声。', self.speech_control))
        self.speech_control.toggled.connect(lambda value: self._save_speech(value))
        status = QLabel('未启用时零主动请求。开启后等待合适时机；缺少凭据时不请求网络。')
        status.setWordWrap(True)
        rows.append(SettingRow('proactive_chat_status', '运行与费用', '每日请求硬上限为展示额度的两倍，每次最多96输出token；模型失败有界退避。默认全天可用，仍尊重锁屏、全屏和手动聊天。', status, stacked=True))
        if values.get('range_review'):
            notice = QLabel('旧设置已安全暂停，原值保留：'+str(values['legacy_ranges'])+'。确认采用当前范围后才能重新开启。')
            notice.setWordWrap(True)
            rows.append(SettingRow('proactive_chat_range_review', '旧配置需要确认', '不会自动缩短原安静时间，也不会把原0条改成自动发言。', notice, stacked=True))
        super().__init__('主动 AI 陪伴', rows, parent)
        for key, control in self.controls.items():
            signal = control.toggled if isinstance(control, ToggleSwitch) else control.valueChanged
            signal.connect(lambda value, key=key: self._save(key, value))
        self._dependencies()

    def _save_speech(self, value):
        from .head_speech import save_toggle
        save_toggle(self, value, active=True)

    def _dependencies(self):
        for key, control in self.controls.items():
            if key != 'enabled':
                control.setEnabled(self.controls['enabled'].isChecked())

    def _save(self, key, value):
        self.config.reload()
        values = normalize_config(self.config.get('proactive_chat'))
        if key == 'enabled' and value and values.get('range_review'):
            choice = QMessageBox.question(self, '采用新的陪伴范围？',
                '原配置为'+str(values['legacy_ranges'])+'，当前界面为'+str(values['daily_limit'])+'条/天、'
                +str(values['min_interval_minutes'])+'分钟。确认后按当前值开启；原值仍保留用于回退。')
            if choice != QMessageBox.StandardButton.Yes:
                self.controls['enabled'].blockSignals(True)
                self.controls['enabled'].setChecked(False)
                self.controls['enabled'].blockSignals(False)
                return
            values['range_review'] = False
        if key == 'enabled':
            from .proactive_policy import set_enabled
            set_enabled(self.config.path, value)
        values[key] = value
        self.config.set('proactive_chat', values)
        if not self.config.save():
            QMessageBox.warning(self, '陪伴设置保存失败', '本次选择保留在当前进程；请检查用户目录权限并重试保存。')
        self._dependencies()
