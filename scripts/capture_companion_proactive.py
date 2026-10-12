"""Capture actual shared settings rows using only synthetic temporary configuration."""
import argparse
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QScrollArea
from capture_settings_pages import _apply_dark_palette
from pet.config import Config
from pet.modern_settings_dialog import ModernSettingsDialog
from pet.settings_widgets import SettingRow

parser = argparse.ArgumentParser()
parser.add_argument('destination')
parser.add_argument('--width', type=int, default=720)
parser.add_argument('--dark', action='store_true')
args = parser.parse_args()
app = QApplication.instance() or QApplication([])
if args.dark:
    _apply_dark_palette(app)
target = Path(args.destination)
target.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='pet-proactive-capture-') as directory:
    cfg = Config(base=Path(directory))
    dialog = ModernSettingsDialog(cfg, include_ai=True)
    dialog.resize(args.width, 800)
    dialog.show()
    index = next(i for i in range(dialog.sidebar.count()) if dialog.sidebar.item(i).text() == 'AI 与对话')
    dialog.sidebar.setCurrentRow(index)
    app.processEvents()
    scroll = dialog.pages.currentWidget().findChild(QScrollArea, 'settingsScroll')
    for enabled in [False, True]:
        dialog.ai_page.proactive_settings.controls['enabled'].setChecked(enabled)
        for part, key in [('controls', 'enabled'), ('limits', 'daily_limit')]:
            row = dialog.findChild(SettingRow, 'settingRow_proactive_chat_'+key)
            scroll.verticalScrollBar().setValue(max(0, row.mapTo(scroll.widget(), QPoint()).y()-40))
            app.processEvents()
            assert dialog.grab().save(str(target/f'{part}-{enabled}.png'))
    dialog.reject()
