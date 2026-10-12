"""Synthetic, local-only P2 microbenchmarks; never reads actual user state."""
import json
import statistics
import sys
import tempfile
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pet.companion.proactive_config import normalize_config
from pet.companion.proactive_repeat import repeats
from pet.companion.proactive_schedule import Scheduler, Snapshot
from pet.companion.proactive_state import ProactiveState


def measure(name, action, count):
    samples = []
    for _ in range(count):
        start = time.perf_counter_ns()
        action()
        samples.append((time.perf_counter_ns()-start)/1000)
    print(f'{name}: n={count} median_us={statistics.median(samples):.2f} p95_us={sorted(samples)[int(count*.95)]:.2f}')


with tempfile.TemporaryDirectory(prefix='pet-proactive-benchmark-') as directory:
    config = normalize_config({'enabled': True})
    now = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
    state = ProactiveState(Path(directory)/'companion_proactive.sqlite3')
    token = state.reserve('seed', 'care', now, config, 'fake-provider')
    recent = [dict(text=f'合成历史话题编号{i}，陪伴测试示例。', tags=json.dumps(['care']), utc=0) for i in range(100)]
    scheduler = Scheduler()
    measure('scheduler_pure_tick', lambda: scheduler.candidates(Snapshot(), now, time.monotonic(), config), 10000)
    measure('disabled_reservation_no_io', lambda: state.reserve('new', 'drink', now, {**config, 'enabled': False}, 'fake-provider'), 10000)
    measure('sqlite_denied_reservation', lambda: state.reserve('new', 'drink', now, config, 'fake-provider'), 500)
    measure('semantic_recent_100', lambda: repeats('清风吹过，也许可以看看窗外。', recent, now.timestamp(), True, 'greeting'), 500)
    tracemalloc.start()
    for _ in range(2000):
        state.recent()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f'2000 SQLite reads Python allocations: current_bytes={current} peak_bytes={peak}; db_bytes={state.path.stat().st_size}')
    state.release(token)
