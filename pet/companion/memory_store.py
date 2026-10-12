"""Local SQLite memory. Each operation owns and closes its thread-local connection.

SQLite short transactions serialize writers; DELETE journal mode until WAL is
validated on Windows 10. Never reset a damaged or newer database automatically.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
import uuid
from .memory_extract import normalize, sensitive


class MemoryUnavailable(Exception):
    """Non-sensitive failure surfaced by the optional capability boundary."""


@dataclass(frozen=True)
class Memory:
    id: str
    topic: str
    content: str
    kind: str
    source: str
    updated_at: str


class MemoryStore:
    MAX_ROWS = 500

    def __init__(self, path, subject='local-owner'):
        self.path = Path(path)
        self.subject = subject

    @contextmanager
    def _db(self, write=False):
        db = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.path, timeout=0.3)
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA busy_timeout=300')
            db.execute('PRAGMA secure_delete=ON')
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, 2):
                raise MemoryUnavailable('不支持的记忆数据库版本；原文件已保留。')
            if version == 1:
                # Consistent pre-migration snapshot; never copy a live SQLite file.
                backup_path = self.path.with_name(self.path.name + '.backup-v1-' + uuid.uuid4().hex)
                target = sqlite3.connect(backup_path)
                try:
                    db.backup(target)
                finally:
                    target.close()
            # Serialize initial schema creation too, including simultaneous first runs.
            db.execute('BEGIN IMMEDIATE' if write or version < 2 else 'BEGIN')
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version == 0:
                db.execute('CREATE TABLE IF NOT EXISTS memory_meta (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL)')
                db.execute('INSERT OR IGNORE INTO memory_meta VALUES (1,0)')
                db.execute('''CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY, subject TEXT NOT NULL, topic TEXT NOT NULL,
                    content TEXT NOT NULL, kind TEXT NOT NULL, source TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    UNIQUE(subject, topic))''')
                db.execute('PRAGMA user_version=1')
            if version < 2:
                db.execute("ALTER TABLE memories ADD COLUMN content_key TEXT NOT NULL DEFAULT ''")
                seen = set()
                for row in db.execute('SELECT id,subject,content FROM memories ORDER BY updated_at DESC,id').fetchall():
                    key = (row['subject'], normalize(row['content']))
                    if key in seen:
                        db.execute('DELETE FROM memories WHERE id=?', (row['id'],))
                    else:
                        seen.add(key)
                        db.execute('UPDATE memories SET content_key=? WHERE id=?', (key[1], row['id']))
                db.execute('CREATE UNIQUE INDEX memory_content_unique ON memories(subject,content_key)')
                db.execute('PRAGMA user_version=2')
            yield db
            db.commit()
        except (sqlite3.Error, OSError) as exc:
            if db is not None:
                db.rollback()
            raise MemoryUnavailable('记忆数据库暂不可用；原文件已保留。') from exc
        finally:
            if db is not None:
                db.close()

    def revision(self):
        with self._db() as db:
            return db.execute('SELECT revision FROM memory_meta WHERE id=1').fetchone()[0]

    @staticmethod
    def _validate(content):
        if not isinstance(content, str) or not content.strip() or len(content.strip()) > 240:
            raise ValueError('记忆需为 1–240 字的非空文本。')
        if sensitive(content):
            raise ValueError('请勿保存凭据、支付信息或健康病史。')
        return content.strip()

    def _put(self, db, topic, content, kind, source):
        content = self._validate(content)
        if kind not in {'fact', 'preference', 'event'} or source not in {'explicit', 'statement', 'manual'}:
            raise ValueError('无效的记忆类型或来源。')
        if not isinstance(topic, str) or not topic or len(topic) > 260:
            raise ValueError('无效的记忆主题。')
        now = datetime.now(timezone.utc).isoformat()
        old = db.execute('SELECT id, content FROM memories WHERE subject=? AND topic=?', (self.subject, topic)).fetchone()
        duplicate = db.execute('SELECT id FROM memories WHERE subject=? AND content_key=?', (self.subject, normalize(content))).fetchone()
        if duplicate:
            if old and old['id'] != duplicate['id']:
                db.execute('DELETE FROM memories WHERE id=?', (old['id'],))
            # Preserve the semantic topic when a confirmed statement merges with
            # a manual record, so the next changed preference replaces it.
            if source != 'manual':
                db.execute('UPDATE memories SET topic=?,kind=?,source=?,updated_at=? WHERE id=?',
                    (topic, kind, source, now, duplicate['id']))
            return duplicate['id']
        ident = old['id'] if old else uuid.uuid4().hex
        if old and normalize(old['content']) == normalize(content):
            return ident
        db.execute('''INSERT INTO memories(id,subject,topic,content,kind,source,created_at,updated_at,content_key) VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(subject,topic) DO UPDATE SET content=excluded.content,
            kind=excluded.kind, source=excluded.source, updated_at=excluded.updated_at, content_key=excluded.content_key''',
            (ident, self.subject, topic, content, kind, source, now, now, normalize(content)))
        db.execute('''DELETE FROM memories WHERE id IN (
            SELECT id FROM memories WHERE subject=? ORDER BY updated_at DESC, id LIMIT -1 OFFSET ?)''',
            (self.subject, self.MAX_ROWS))
        return ident

    def put(self, topic, content, kind='fact', source='manual'):
        with self._db(True) as db:
            ident = self._put(db, topic, content, kind, source)
            db.execute('UPDATE memory_meta SET revision=revision+1 WHERE id=1')
            row = db.execute('SELECT * FROM memories WHERE id=?', (ident,)).fetchone()
            return self._row(row)

    def remember(self, candidates, expected_revision, *, allowed=None):
        with self._db(True) as db:
            if allowed is not None and not allowed():
                return False
            if db.execute('SELECT revision FROM memory_meta WHERE id=1').fetchone()[0] != expected_revision:
                return False
            for candidate in candidates:
                self._put(db, candidate.topic, candidate.content, candidate.kind, candidate.source)
            if candidates:
                db.execute('UPDATE memory_meta SET revision=revision+1 WHERE id=1')
            return True

    @staticmethod
    def _row(row):
        return Memory(*(row[key] for key in ('id', 'topic', 'content', 'kind', 'source', 'updated_at')))

    def list(self):
        with self._db() as db:
            return [self._row(r) for r in db.execute('SELECT * FROM memories WHERE subject=? ORDER BY updated_at DESC,id', (self.subject,))]

    def edit(self, ident, content):
        content = self._validate(content)
        with self._db(True) as db:
            existing = db.execute('SELECT id FROM memories WHERE subject=? AND content_key=? AND id!=?', (self.subject, normalize(content), ident)).fetchone()
            if existing:
                db.execute('DELETE FROM memories WHERE id=? AND subject=?', (ident, self.subject))
            else:
                db.execute('UPDATE memories SET content=?, content_key=?, source=?, updated_at=? WHERE id=? AND subject=?',
                    (content, normalize(content), 'manual', datetime.now(timezone.utc).isoformat(), ident, self.subject))
            db.execute('UPDATE memory_meta SET revision=revision+1 WHERE id=1')

    def delete(self, ident):
        with self._db(True) as db:
            db.execute('DELETE FROM memories WHERE id=? AND subject=?', (ident, self.subject))
            db.execute('UPDATE memory_meta SET revision=revision+1 WHERE id=1')

    def clear(self):
        with self._db(True) as db:
            db.execute('DELETE FROM memories WHERE subject=?', (self.subject,))
            db.execute('UPDATE memory_meta SET revision=revision+1 WHERE id=1')

    def search(self, query, limit=5, char_limit=600):
        def tokens(text):
            text = normalize(text)
            english = set(re.findall(r'[a-z0-9]+', text))
            chinese = {text[i:i+2] for i in range(len(text)-1) if all('\u4e00' <= c <= '\u9fff' for c in text[i:i+2])}
            return english | chinese
        wanted = tokens(query)
        ranked = []
        aliases = {'preference:color': '喜欢颜色', 'fact:name': '名字称呼姓名'}
        for row in self.list():
            score = len(wanted & tokens(row.content + aliases.get(row.topic, row.topic)))
            if score:
                ranked.append((score, row))
        ranked.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
        result, used = [], 0
        for _, row in ranked:
            if len(result) >= max(0, min(limit, 5)):
                break
            if used + len(row.content) <= max(0, min(char_limit, 600)):
                result.append(row)
                used += len(row.content)
        return result

    def backup(self, destination):
        destination = Path(destination)
        if destination.resolve() == self.path.resolve() or destination.exists():
            raise ValueError('备份目标必须是新的独立文件。')
        with self._db() as db:
            target = sqlite3.connect(destination)
            try:
                db.backup(target)
            finally:
                target.close()
