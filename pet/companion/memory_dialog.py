"""Explicit local memory management; database jobs never run on the UI thread."""
import threading
import uuid
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QVBoxLayout, QMessageBox,
)
from ..chat.utils import _safe_emit
from ..settings_widgets import ResponsiveActionRow
from .memory_store import MemoryStore, MemoryUnavailable
from .memory_extract import normalize


class MemoryDialog(QDialog):
    done = Signal(object, str)

    def __init__(self, directory, parent=None):
        super().__init__(parent)
        self.setWindowTitle('长期记忆管理')
        self.resize(720, 600)
        self.setMinimumSize(480, 420)
        self.path = directory / 'companion_memory.sqlite3'
        self._busy = False
        root = QVBoxLayout(self)
        self.help = QLabel('仅保存在此用户数据目录中。启用记忆后，相关内容会随聊天发送给当前模型服务。\n删除记忆不会删除原聊天历史；如需彻底遗忘，请同时清理相关会话。')
        self.help.setWordWrap(True)
        root.addWidget(self.help)
        self.items = QListWidget(self)
        self.items.setAccessibleName('已保存的长期记忆')
        root.addWidget(self.items, 1)
        self.editor = QPlainTextEdit(self)
        self.editor.setPlaceholderText('选择一条记忆进行修改，或输入已确认事实新增（最多 240 字）')
        self.editor.setAccessibleName('记忆内容')
        root.addWidget(self.editor)
        self.add_button = QPushButton('新增', self)
        self.save_button = QPushButton('保存修改', self)
        self.delete_button = QPushButton('删除所选', self)
        self.clear_button = QPushButton('删除全部', self)
        self.backup_button = QPushButton('备份', self)
        root.addWidget(ResponsiveActionRow(self.add_button, [self.save_button, self.delete_button, self.clear_button, self.backup_button], self))
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        self.status.setAccessibleName('记忆操作结果')
        root.addWidget(self.status)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        close.rejected.connect(self.reject)
        root.addWidget(close)
        self.items.currentItemChanged.connect(self._selected)
        self.add_button.clicked.connect(self._add)
        self.save_button.clicked.connect(self._edit)
        self.delete_button.clicked.connect(self._delete)
        self.clear_button.clicked.connect(self._clear)
        self.backup_button.clicked.connect(self._backup)
        self.done.connect(self._done, Qt.ConnectionType.QueuedConnection)
        self._job('list')

    def _selected(self, item, previous=None):
        self.editor.setPlainText(item.data(Qt.ItemDataRole.UserRole).content if item else '')
        self._controls()

    def _controls(self):
        selected = self.items.currentItem() is not None
        for button in (self.add_button, self.clear_button, self.backup_button):
            button.setEnabled(not self._busy)
        for button in (self.save_button, self.delete_button):
            button.setEnabled(not self._busy and selected)
        self.items.setEnabled(not self._busy)
        self.editor.setEnabled(not self._busy)

    def _job(self, operation, *args):
        if self._busy:
            return
        self._busy = True
        self._controls()
        self.status.setText('正在处理…')
        path = self.path
        def work():
            try:
                store = MemoryStore(path)
                if operation != 'list':
                    getattr(store, operation)(*args)
                rows = store.list()
                _safe_emit(self, 'done', rows, '')
            except (MemoryUnavailable, ValueError, OSError) as exc:
                # Domain errors contain no transcript/SQL/credential data.
                message = str(exc) if isinstance(exc, (MemoryUnavailable, ValueError)) else '本地文件操作失败。'
                _safe_emit(self, 'done', None, message)
        threading.Thread(target=work, daemon=True, name='pet-memory-management').start()

    def _done(self, rows, error):
        self._busy = False
        if rows is not None:
            self.items.clear()
            for row in rows:
                item = QListWidgetItem(row.content)
                item.setData(Qt.ItemDataRole.UserRole, row)
                item.setToolTip(f'{row.kind} · {row.source} · {row.updated_at}')
                self.items.addItem(item)
            self.status.setText(f'已完成，当前共 {len(rows)} 条记忆。备份仅存本地，删除记忆不删除已有备份。')
        else:
            self.status.setText(error)
        self._controls()

    def _add(self):
        content = self.editor.toPlainText().strip()
        self._job('put', 'manual:' + normalize(content), content, 'fact', 'manual')

    def _edit(self):
        item = self.items.currentItem()
        if item:
            self._job('edit', item.data(Qt.ItemDataRole.UserRole).id, self.editor.toPlainText())

    def _delete(self):
        item = self.items.currentItem()
        if item:
            self._job('delete', item.data(Qt.ItemDataRole.UserRole).id)

    def _clear(self):
        if QMessageBox.question(self, '删除全部长期记忆', '删除全部记忆？在途的旧提取结果将失效。聊天历史与备份不会被删除。') == QMessageBox.StandardButton.Yes:
            self._job('clear')

    def _backup(self):
        self._job('backup', self.path.with_name(self.path.name + '.backup-' + uuid.uuid4().hex))
