"""Worker-only bounded durable reservations. Never reset a damaged database.

A crash after presentation begins leaves a conservative held slot until the
local day ends. SQLite cannot transact atomically with a desktop window.
"""
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta
import json
import sqlite3
import uuid
from .proactive_config import normalize_config


class StateUnavailable(Exception):
    pass


class ProactiveState:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def db(self):
        conn = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, timeout=.3)
            conn.row_factory = sqlite3.Row
            conn.execute('BEGIN IMMEDIATE')
            version = conn.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, 2):
                raise StateUnavailable('unsupported proactive state version')
            if not version:
                for sql in [
                    'CREATE TABLE days(day TEXT PRIMARY KEY, successes INTEGER, attempts INTEGER, tokens INTEGER)',
                    'CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)',
                    'CREATE TABLE reservations(id TEXT PRIMARY KEY, event TEXT, day TEXT, category TEXT, status TEXT, utc REAL, expires REAL, attempts INTEGER)',
                    'CREATE TABLE utterances(id TEXT PRIMARY KEY, event TEXT, text TEXT, tags TEXT, utc REAL, day TEXT)',
                ]:
                    conn.execute(sql)
                conn.execute('PRAGMA user_version=1')
            if version < 2:
                conn.execute('ALTER TABLE reservations ADD COLUMN quota INTEGER NOT NULL DEFAULT 10')
                conn.execute('ALTER TABLE reservations ADD COLUMN spacing INTEGER NOT NULL DEFAULT 1800')
                tentative = conn.execute("SELECT id,utc FROM reservations WHERE status='presenting' ORDER BY utc DESC LIMIT 1").fetchone()
                if tentative:
                    self.set(conn, 'tentative_id', tentative['id'])
                    self.set(conn, 'tentative_utc', tentative['utc']+5)
                conn.execute('PRAGMA user_version=2')
            yield conn
            conn.commit()
        except (sqlite3.Error, OSError) as exc:
            if conn:
                conn.rollback()
            raise StateUnavailable('proactive state unavailable') from exc
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get(db, key, default=''):
        row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return row[0] if row else default

    @staticmethod
    def set(db, key, value):
        db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key, str(value)))

    def reserve(self, event, category, now, config, signature):
        config = normalize_config(config)
        if not config['enabled'] or not config['daily_limit']:
            return None
        utc, day = now.timestamp(), now.date().isoformat()
        expires = min(utc+60, (now.replace(hour=0, minute=0, second=0, microsecond=0)+timedelta(days=1)).timestamp()-5)
        if expires <= utc:
            return None  # Five-second midnight fence; not a night-time quiet period.
        interval = config['min_interval_minutes'] * 60
        with self.db() as db:
            if self.get(db, 'blocked') == signature or utc < float(self.get(db, 'retry', 0)):
                return None
            highwater = float(self.get(db, 'highwater', 0))
            if utc < highwater:
                return None
            self.set(db, 'highwater', utc)
            # Long gaps never release ambiguous presenting claims into the same day's quota.
            db.execute("DELETE FROM reservations WHERE status='pending' AND expires<=?", (utc,))
            db.execute('DELETE FROM reservations WHERE day<? AND expires<?', (day, utc))
            db.execute('DELETE FROM utterances WHERE utc<?', (utc-30*86400,))
            db.execute('DELETE FROM days WHERE day<?', ((now.date().fromordinal(now.date().toordinal()-60)).isoformat(),))
            db.execute('INSERT OR IGNORE INTO days VALUES (?,0,0,0)', (day,))
            counts = db.execute('SELECT * FROM days WHERE day=?', (day,)).fetchone()
            held = db.execute('SELECT COUNT(*) FROM reservations WHERE day=?', (day,)).fetchone()[0]
            if counts['successes'] + held >= config['daily_limit'] or counts['attempts'] >= config['daily_limit']*2:
                return None
            if db.execute("SELECT 1 FROM reservations WHERE status='pending'").fetchone():
                return None
            last = float(self.get(db, 'last', 0))
            ambiguous = max(float(self.get(db, 'tentative_utc', 0)), db.execute("SELECT MAX(utc) FROM reservations WHERE status='presenting'").fetchone()[0] or 0)
            if utc-max(last, ambiguous) < interval:
                return None
            if db.execute('SELECT 1 FROM reservations WHERE event=? UNION SELECT 1 FROM utterances WHERE event=?', (event, event)).fetchone():
                return None
            recent = db.execute('SELECT tags,utc FROM utterances ORDER BY utc DESC LIMIT 100').fetchall()
            cooldown = 6*3600 if category == 'greeting' else 2*3600
            if any(category in json.loads(r['tags']) and utc-r['utc'] < cooldown for r in recent):
                return None
            token = uuid.uuid4().hex
            db.execute('INSERT INTO reservations VALUES (?,?,?,?,?,?,?,1,?,?)', (token, event, day, category, 'pending', utc, expires, config['daily_limit'], interval))
            db.execute('UPDATE days SET attempts=attempts+1,tokens=tokens+96 WHERE day=?', (day,))
            return token

    def retry_attempt(self, token, config, now=None):
        config = normalize_config(config)
        now = now or datetime.now().astimezone()
        with self.db() as db:
            r = db.execute('SELECT * FROM reservations WHERE id=?', (token,)).fetchone()
            if (not r or r['attempts'] >= 2 or r['status'] != 'pending'
                    or r['day'] != now.date().isoformat() or not r['utc'] <= now.timestamp() < r['expires']):
                return False
            row = db.execute('SELECT attempts FROM days WHERE day=?', (r['day'],)).fetchone()
            if row[0] >= config['daily_limit']*2:
                return False
            db.execute('UPDATE reservations SET attempts=attempts+1 WHERE id=?', (token,))
            db.execute('UPDATE days SET attempts=attempts+1,tokens=tokens+96 WHERE day=?', (r['day'],))
            return True

    def mark_presenting(self, token, now):
        with self.db() as db:
            utc, day = now.timestamp(), now.date().isoformat()
            r = db.execute("SELECT * FROM reservations WHERE id=? AND status='pending'", (token,)).fetchone()
            if not r or r['day'] != day or not r['utc'] <= utc < r['expires']:
                return False
            counts = db.execute('SELECT successes FROM days WHERE day=?', (day,)).fetchone()
            held = db.execute('SELECT COUNT(*) FROM reservations WHERE day=?', (day,)).fetchone()[0]
            if not counts or not 0 <= counts[0] or counts[0]+held > min(10, r['quota']):
                return False
            last = max(float(self.get(db, 'last', 0)), float(self.get(db, 'tentative_utc', 0)))
            if utc-last < r['spacing']:
                return False
            db.execute("UPDATE reservations SET status='presenting',utc=? WHERE id=?", (utc, token))
            self.set(db, 'tentative_id', token)
            self.set(db, 'tentative_utc', utc+5)  # Upper bound of a valid UI handoff.
            return True

    def finish(self, token, text, tags, now, shown):
        with self.db() as db:
            r = db.execute("SELECT * FROM reservations WHERE id=? AND status='presenting'", (token,)).fetchone()
            if not r:
                return False
            if shown is True:
                day = now.date().isoformat()
                # Credit belongs to the pre-presentation claim's local day.
                # A late/different-day receipt cannot sell a new day's slot.
                if (day != r['day'] or not r['utc'] <= now.timestamp() <= r['utc']+5
                        or now.timestamp() >= r['expires']):
                    return False
                counts = db.execute('SELECT successes FROM days WHERE day=?', (day,)).fetchone()
                held = db.execute('SELECT COUNT(*) FROM reservations WHERE day=?', (day,)).fetchone()[0]
                if not counts or counts[0]+held > min(10, r['quota']):
                    return False
                updated = db.execute('UPDATE days SET successes=successes+1 WHERE day=? AND successes>=0 AND successes<?', (day, min(10, r['quota']))).rowcount
                if updated != 1:
                    return False  # Preserve the ambiguous claim, never invent success.
                self.set(db, 'last', max(float(self.get(db, 'last', 0)), now.timestamp()))
                self.set(db, 'failures', 0)
                db.execute('INSERT INTO utterances VALUES (?,?,?,?,?,?)', (token, r['event'], text[:80], json.dumps(tags), now.timestamp(), day))
                db.execute('DELETE FROM utterances WHERE id NOT IN (SELECT id FROM utterances ORDER BY utc DESC LIMIT 100)')
            elif shown is not False:
                return False
            self._clear_tentative(db, token)
            db.execute('DELETE FROM reservations WHERE id=?', (token,))
            return True

    def _clear_tentative(self, db, token):
        if self.get(db, 'tentative_id') == token:
            db.execute("DELETE FROM meta WHERE key IN ('tentative_id','tentative_utc')")

    def release(self, token):
        with self.db() as db:
            self._clear_tentative(db, token)
            db.execute('DELETE FROM reservations WHERE id=?', (token,))

    def failure(self, status, retry_after, now, signature):
        with self.db() as db:
            if status == 401:
                self.set(db, 'blocked', signature)
            failures = min(6, int(self.get(db, 'failures', 0))+1)
            self.set(db, 'failures', failures)
            delay = max(min(86400, max(0, retry_after or 0)), min(3600, 60*2**failures))
            self.set(db, 'retry', now.timestamp()+delay)

    def recent(self):
        with self.db() as db:
            return [dict(r) for r in db.execute('SELECT * FROM utterances ORDER BY utc DESC LIMIT 100')]

    def request_window(self, token):
        with self.db() as db:
            r = db.execute('SELECT day,expires FROM reservations WHERE id=?', (token,)).fetchone()
            return dict(r) if r else None

    def stats(self, day):
        with self.db() as db:
            row = db.execute('SELECT * FROM days WHERE day=?', (day,)).fetchone()
            return dict(row) if row else dict(successes=0, attempts=0, tokens=0)
