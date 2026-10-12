"""Synthetic local-memory benchmark; never opens real user data."""
import sys, tempfile, statistics, time, tracemalloc, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pet.companion.memory_store import MemoryStore
from pet.companion.memory_extract import extract_memories
from pet.companion.memory_context import MemoryContext
from pet.chat.prompt import PromptBuilder
from pet.chat.models import ChatSettings

def measure(name, f, n):
    times=[]
    for _ in range(n):
        start=time.perf_counter()
        f()
        times.append((time.perf_counter()-start)*1000)
    times.sort()
    print(f'{name}: n={n}, median_ms={statistics.median(times):.4f}, p95_ms={times[int(n*.95)-1]:.4f}')
with tempfile.TemporaryDirectory() as d:
    store=MemoryStore(Path(d)/'m.db')
    for i in range(500): store.put(f'event:{i}', f'我最近要参加考试{i}', 'event', 'manual')
    measure('read_search_500_rows', lambda:store.search('考试'),100)
    measure('write_dedup', lambda:store.put('event:499','我最近要参加考试499','event','manual'),100)
    measure('extract_local',lambda:extract_memories('我喜欢蓝色。请记住我下周要考试。',True),1000)
    builder=PromptBuilder(); settings=ChatSettings.defaults()
    baseline_source = subprocess.check_output(['git', 'show', '27495f9b67bd7529c633392927b185e9a2ccd685:pet/chat/prompt.py'], text=True)
    namespace = {'__package__': 'pet.chat'}
    exec(baseline_source, namespace)
    baseline = namespace['PromptBuilder']()
    measure('prompt_baseline', lambda:baseline.build_messages(settings,'fish',[],'你好'),1000)
    measure('prompt_disabled', lambda:builder.build_messages(settings,'fish',[],'你好'),1000)
    context=MemoryContext(store.path,'你好',False)
    measure('worker_memory_disabled',lambda:context.prepare([{'role':'user','content':'你好'}]),1000)
    tracemalloc.start()
    for _ in range(20):store.search('考试')
    before=tracemalloc.get_traced_memory()[0]
    for _ in range(100):store.search('考试')
    current, peak=tracemalloc.get_traced_memory()
    print(f'retrieval_python_bytes: retained_delta={current-before}, peak={peak}; sqlite_bytes={store.path.stat().st_size}')
