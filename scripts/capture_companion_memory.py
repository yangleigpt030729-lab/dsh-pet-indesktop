"""Capture P1 settings and memory management with synthetic local data only."""
import argparse
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QScrollArea
from capture_settings_pages import _apply_dark_palette
from pet.config import Config
from pet.modern_settings_dialog import ModernSettingsDialog
from pet.settings_widgets import SettingRow
from pet.companion.memory_dialog import MemoryDialog
from pet.companion.memory_store import MemoryStore

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
with tempfile.TemporaryDirectory(prefix='pet-memory-capture-') as d:
    cfg = Config(base=Path(d))
    settings = ModernSettingsDialog(cfg, include_ai=True)
    settings.resize(args.width, 800)
    settings.show()
    index = next(i for i in range(settings.sidebar.count()) if settings.sidebar.item(i).text() == 'AI 与对话')
    settings.sidebar.setCurrentRow(index)
    app.processEvents()
    scroll = settings.pages.currentWidget().findChild(QScrollArea, 'settingsScroll')
    row = settings.findChild(SettingRow, 'settingRow_memory_enabled')
    scroll.verticalScrollBar().setValue(max(0, row.mapTo(scroll.widget(), QPoint()).y() - 60))
    app.processEvents()
    assert settings.grab().save(str(target / 'settings-memory.png'))
    MemoryStore(cfg.dir / 'companion_memory.sqlite3').put('preference:color', '我喜欢蓝色（合成示例）', 'preference', 'manual')
    manager = MemoryDialog(cfg.dir, settings)
    manager.resize(max(480, args.width - 160), 600)
    manager.show()
    deadline = time.monotonic() + 10
    while manager._busy and time.monotonic() < deadline:
        app.processEvents()
    assert not manager._busy and manager.items.count() == 1
    manager.items.setCurrentRow(0)
    app.processEvents()
    assert manager.grab().save(str(target / 'manager-memory.png'))
    manager.reject()
    settings.reject()
