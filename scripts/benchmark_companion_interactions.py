"""Bounded local interaction costs; synthetic input, no private data/network."""
import sys
import tempfile
import time
import statistics
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psutil
from PySide6.QtCore import QPointF, QRect
from PySide6.QtWidgets import QApplication
from pet.companion.feeding_metadata import describe
from pet.companion.touch_region import head_core_at
from pet.companion.interaction_service import InteractionService
from pet.companion.expression_style import context, message
from pet.companion.head_speech import permission_stamp
from pet.config import Config
from scripts.run_companion_acceptance import install_fake_chat


def wait(app, condition):
    deadline = time.monotonic()+60
    while not condition():
        app.processEvents()
        if time.monotonic() > deadline:
            raise TimeoutError('bounded benchmark event deadline')
        time.sleep(.001)


def main():
    install_fake_chat()
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as directory:
        cfg = Config(base=Path(directory))
        cfg.set('companion_interaction', {'head_touch_enabled': True})
        cfg.save()
        start = time.perf_counter()
        for _ in range(20000):
            message(context(cfg))
        style_us = (time.perf_counter()-start)*1e6/20000
        start = time.perf_counter()
        for _ in range(20000):
            permission_stamp(cfg)
        permission_us = (time.perf_counter()-start)*1e6/20000
        class Target:
            key = 'synthetic'
            def config(self):
                return cfg
            def identity(self):
                return 'synthetic'
            def valid(self):
                return True
            def manual_busy(self):
                return False
            def present(self, text):
                return True
        now = [10000.]
        service = InteractionService(monotonic=lambda: now[0])
        delivered = []
        service.delivered.connect(lambda *args: delivered.append(True))
        target = Target()
        costs = []
        start = time.perf_counter()
        accepted = sum(service.request('head', target) for _ in range(1000))
        burst_ms = (time.perf_counter()-start)*1000
        wait(app, lambda: not service.busy)
        rss = []
        process = psutil.Process()
        for n in range(200):
            # Keep the clock fixed: successful requests may follow immediately.
            start = time.perf_counter()
            assert service.request('head', target)
            wait(app, lambda: not service.busy)
            costs.append((time.perf_counter()-start)*1000)
            rss.append(process.memory_info().rss/1024**2)
        service.close()
        assert len(delivered) == 201 and accepted == 1
        rect, point = QRect(19, 31, 640, 360), QPointF(324, 141)
        start = time.perf_counter()
        for _ in range(20000):
            assert head_core_at('shenshen', point, rect, False)
        core_us = (time.perf_counter()-start)*1e6/20000
        path = Path(directory)/'synthetic.py'
        path.write_text('synthetic')
        stats = []
        for _ in range(200):
            start = time.perf_counter()
            describe([path])
            stats.append((time.perf_counter()-start)*1000)
        folder = Path(directory)/'large'
        folder.mkdir()
        for n in range(5001):
            (folder/str(n)).touch()
        start = time.perf_counter()
        large = describe([folder])
        large_ms = (time.perf_counter()-start)*1000
        assert large['partial'] and not list(cfg.dir.glob('*.sqlite3'))
        print(json.dumps(dict(head_core_n=20000, head_core_us=core_us,
            style_n=20000, style_context_message_us=style_us, permission_n=20000, permission_stamp_us=permission_us,
            stat_file_n=200, stat_file_median_ms=statistics.median(stats), stat_file_max_ms=max(stats),
            directory_entries=5001, directory_ms=large_ms, directory_partial=large['partial'],
            burst_n=1000, burst_accepted=accepted, burst_ms=burst_ms,
            completed_n=200, synthetic_median_ms=statistics.median(costs), synthetic_max_ms=max(costs),
            rss_warm_mib=rss[19], rss_last_mib=rss[-1], pending_feed_targets=len(service.pending_feeds),
            recent_count=len(service.recent), workers_remaining=len(service.chat._workers)), indent=2))


if __name__ == '__main__':
    main()
