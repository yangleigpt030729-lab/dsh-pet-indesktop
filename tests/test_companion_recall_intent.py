import pytest
from pet.companion.memory_store import MemoryStore
from pet.companion.memory_context import MemoryContext


@pytest.mark.parametrize('query', ['火星的颜色是什么？', '我想知道火星的颜色是什么？', '请帮我解释蓝色光的物理原理', '你喜欢什么颜色？', '我想学习配色', '不要读取我的长期记忆', '我想让你告诉我蓝色的物理原理', '我想问你以前说过哪些颜色名称'])
def test_ordinary_query_never_opens_memory(tmp_path, monkeypatch, query):
    def forbidden(*args, **kwargs):
        pytest.fail('ordinary query opened private SQLite')
    monkeypatch.setattr(MemoryStore, '_db', forbidden)
    assert MemoryStore(tmp_path / 'm.db').search(query) == []
    messages = [{'role': 'system', 'content': '鱼'}, {'role': 'user', 'content': query}]
    assert MemoryContext(tmp_path / 'm.db', query, True, True).prepare(messages) == (messages, None)


@pytest.mark.parametrize('query', ['我以前说过喜欢什么颜色？', '你还记得我喜欢什么颜色吗？', '我以前告诉过你哪些喜好？', '你还记得我告诉过你什么吗？'])
def test_personal_recall_survives(tmp_path, query):
    store = MemoryStore(tmp_path / 'm.db')
    store.put('preference:color', '我喜欢蓝色', 'preference')
    assert [r.content for r in store.search(query)] == ['我喜欢蓝色']
