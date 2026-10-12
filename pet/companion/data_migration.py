"""Local same-user variant migration; preserve source and existing destinations."""
from pathlib import Path
import shutil
import sqlite3
import time
import os
from contextlib import closing

DATABASES = ('companion_memory.sqlite3', 'companion_proactive.sqlite3')
FILES = ('todo_items.json', 'file_eaten_stats.json', 'proactive_screen_memory.json')
PENDING = 'companion-migration.pending'


def migrate_data(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    success = True
    for name in (*DATABASES, *FILES):
        src, dst = source/name, destination/name
        if not src.is_file() or dst.exists():
            continue
        temporary = dst.with_name(dst.name+f'.{os.getpid()}.tmp')
        try:
            if name in DATABASES:
                # backup handles a live SQLite journal consistently; copying only
                # the .sqlite3 bytes would lose recent transactions under WAL.
                deadline = time.monotonic()+1
                def progress(status, remaining, total):
                    if time.monotonic() > deadline:
                        raise TimeoutError('local migration backup deadline')
                with closing(sqlite3.connect(src.resolve().as_uri()+'?mode=ro', uri=True, timeout=.2)) as reader:
                    reader.execute('PRAGMA schema_version').fetchone()
                    with closing(sqlite3.connect(temporary)) as writer:
                        reader.backup(writer, pages=128, progress=progress, sleep=.01)
            else:
                shutil.copy2(src, temporary)
            if not dst.exists():
                os.replace(temporary, dst)
        except (OSError, sqlite3.Error, TimeoutError):
            success = False
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                success = False
    for src in sorted(source.glob('config-slot-*.json'))[:100] + sorted(source.glob('todo_items-slot-*.json'))[:100]:
        dst = destination/src.name
        if not dst.exists():
            try:
                shutil.copy2(src, dst)
            except OSError:
                success = False
    return success
