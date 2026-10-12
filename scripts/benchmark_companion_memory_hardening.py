"""P1/P1.1 comparison on synthetic temporary data; requires baseline c81f26f."""
import statistics,subprocess,tempfile,time,tracemalloc,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pet.companion.memory_store import MemoryStore
from pet.companion.memory_extract import sensitive,extract_memories
from pet.companion.memory_retrieve import recall_query
baseline={'__package__':'pet.companion'}
exec(subprocess.check_output(['git','show','c81f26f:pet/companion/memory_store.py'],text=True),baseline)
old_filter={}
exec(subprocess.check_output(['git','show','c81f26f:pet/companion/memory_extract.py'],text=True),old_filter)
def measure(name,f,n):
    samples=[]
    for _ in range(n):
        start=time.perf_counter();value=f();samples.append((time.perf_counter()-start)*1000)
    samples.sort()
    count=len(value) if isinstance(value,list) else '-'
    print(f'{name} n={n} median_ms={statistics.median(samples):.4f} p95_ms={samples[int(n*.95)-1]:.4f} returned={count}',flush=True)
with tempfile.TemporaryDirectory() as d:
    store=MemoryStore(Path(d)/'m.db')
    for i in range(300):store.put(f'event:{i}',f'我最近要参加考试{i}','event','manual')
    for i in range(100):store.put(f'preference:{i}',f'我喜欢音乐{i}','preference','manual')
    for i in range(100):store.put(f'fact:{i}',f'我的工作是编程{i}','fact','manual')
    old=baseline['MemoryStore'](store.path)
    measure('P1_topic_exam',lambda:old.search('考试'),100)
    measure('P11_topic_exam',lambda:store.search('考试'),100)
    measure('P1_preferences_overview',lambda:old.search('我以前和你说过哪些喜好'),100)
    measure('P11_preferences_overview',lambda:store.search('我以前和你说过哪些喜好'),100)
    measure('P11_personal_overview',lambda:store.search('你还记得我以前告诉过你什么吗'),100)
    measure('P1_sensitive',lambda:old_filter['sensitive']('我的邮箱是fish@example.com'),1000)
    measure('P11_sensitive',lambda:sensitive('我的邮箱是fish@example.com'),1000)
    measure('P11_extract',lambda:extract_memories('我的邮箱是fish@example.com。我喜欢蓝色',True),1000)
    measure('P11_intent',lambda:recall_query('我以前和你说过哪些喜好'),1000)
    tracemalloc.start()
    for _ in range(20):store.search('我以前和你说过哪些喜好')
    before=tracemalloc.get_traced_memory()[0]
    for _ in range(100):store.search('我以前和你说过哪些喜好')
    current,peak=tracemalloc.get_traced_memory()
    print('retained_delta_bytes=',current-before,'peak_bytes=',peak,'db_bytes=',store.path.stat().st_size,flush=True)
