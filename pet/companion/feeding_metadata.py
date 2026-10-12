"""Bounded local stat-only inspection. Names/paths/content never enter AI metadata."""
from pathlib import Path
import os
import time

EXTENSIONS = {
    'image': {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.heic'},
    'python': {'.py', '.pyw'},
    'code': {'.js', '.ts', '.tsx', '.jsx', '.c', '.cpp', '.h', '.cs', '.java', '.rs', '.go', '.html', '.css', '.sh'},
    'audio': {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac'},
    'video': {'.mp4', '.mkv', '.webm', '.mov', '.avi'},
    'archive': {'.zip', '.7z', '.rar', '.gz', '.tar'},
    'document': {'.txt', '.md', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'},
}


def describe(paths, cancel=None, *, max_entries=5000, max_seconds=.5):
    files = folders = total = visited = 0
    partial = False
    categories = {}
    deadline = time.monotonic()+max_seconds
    for raw in paths:
        if cancel is not None and cancel.is_set():
            return None
        path = Path(raw)
        try:
            if path.is_file():
                files += 1
                total += path.stat().st_size
                category = next((k for k, exts in EXTENSIONS.items() if path.suffix.lower() in exts), 'other')
            elif path.is_dir():
                folders += 1
                category = 'folder'
                for root, dirs, names in os.walk(path, followlinks=False):
                    visited += 1
                    if visited > max_entries or time.monotonic() > deadline or (cancel is not None and cancel.is_set()):
                        partial = True
                        break
                    if len(dirs) > max_entries:
                        partial = True
                        dirs[:] = dirs[:max_entries]
                    dirs[:] = [d for d in dirs if not (Path(root)/d).is_symlink()]
                    for name in names:
                        visited += 1
                        if visited > max_entries or time.monotonic() > deadline or (cancel is not None and cancel.is_set()):
                            partial = True
                            break
                        try:
                            total += (Path(root)/name).stat().st_size
                        except OSError:
                            partial = True
                    if partial:
                        break
            else:
                continue
            categories[category] = categories.get(category, 0)+1
        except OSError:
            partial = True
    bucket = ('unknown' if partial else 'tiny' if total < 1024 else 'small' if total < 1024**2
              else 'medium' if total < 100*1024**2 else 'large')
    return {'files': files, 'folders': folders, 'bytes': total, 'partial': partial,
            'metadata': {'categories': categories, 'files': files, 'folders': folders, 'size_bucket': bucket}}
