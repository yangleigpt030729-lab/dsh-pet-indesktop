"""Persistent interactive QWidgetAction; slider/buttons never trigger QAction."""
from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import QWidget, QWidgetAction, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton
from ..voice_volume import VolumeBinding, menu_config, write
from .shared import add_submenu


def build_volume_menu(menu, pet, *, icons=True):
    submenu = add_submenu(menu, '音量控制', 'volume' if icons else None)
    cfg = menu_config(pet)
    widget = QWidget(submenu)
    widget.setObjectName('speechVolumeControls')
    widget.setFont(submenu.font())
    if submenu.property('menuStyle') == 'modern':
        dark = bool(submenu.property('modernDark'))
        bg, fg, border = ('#2a2a30', '#e0e0e6', '#3a3a42') if dark else ('#ffffff', '#252525', '#e2e4e8')
        widget.setStyleSheet(f"""
            QWidget#speechVolumeControls {{ background:{bg}; color:{fg}; }}
            QLabel {{ color:{fg}; }}
            QPushButton {{ color:{fg}; background:{bg}; border:1px solid {border}; border-radius:7px; padding:5px 10px; }}
            QPushButton:hover {{ background:{'#303036' if dark else '#f4f5f6'}; }}
            QPushButton:pressed {{ background:{'#3a3a46' if dark else '#e3e5e8'}; }}
            QPushButton:focus {{ border:2px solid #0a84ff; }}
            QSlider::groove:horizontal {{ height:4px; background:{border}; border-radius:2px; }}
            QSlider::sub-page:horizontal {{ background:#0a84ff; border-radius:2px; }}
            QSlider::handle:horizontal {{ background:{bg}; border:1px solid #0a84ff; width:14px; margin:-6px 0; border-radius:7px; }}
            QSlider::handle:horizontal:focus {{ border:2px solid #0a84ff; }}
        """)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(14, 10, 14, 10)
    row = QHBoxLayout()
    label = QLabel('语音音量', widget)
    percent = QLabel(widget)
    percent.setObjectName('speechVolumePercent')
    row.addWidget(label)
    row.addStretch()
    row.addWidget(percent)
    layout.addLayout(row)
    slider = QSlider(Qt.Horizontal, widget)
    slider.setObjectName('speechVolumeSlider')
    slider.setRange(0, 100)
    slider.setAccessibleName('微软在线语音音量')
    slider.setAccessibleDescription('0至100%，拖动时解除静音；仅控制桌宠语音。')
    slider.setMinimumWidth(210)
    layout.addWidget(slider)
    mute = QPushButton(widget)
    mute.setObjectName('speechVolumeMute')
    layout.addWidget(mute)
    status = QLabel('只控制桌宠语音', widget)
    status.setWordWrap(True)
    layout.addWidget(status)
    binding = VolumeBinding(cfg, widget)
    def sync(volume, muted):
        blocker = QSignalBlocker(slider)
        slider.setValue(volume)
        del blocker
        percent.setText(f'{volume}%' + (' · 已静音' if muted else ''))
        mute.setText('恢复原音量' if muted else '一键静音')
    def commit(**kw):
        if not write(cfg, **kw):
            status.setText('保存失败，请检查配置目录权限')
            sync(*binding.current)
    slider.valueChanged.connect(lambda n: commit(volume=n))
    mute.clicked.connect(lambda: commit(muted=not binding.current[1]))
    binding.changed.connect(sync)
    submenu.aboutToShow.connect(binding.refresh)
    sync(*binding.current)
    action = QWidgetAction(submenu)
    action.setDefaultWidget(widget)
    submenu.addAction(action)
    submenu.setProperty('speechVolumeControls', True)
    return submenu
