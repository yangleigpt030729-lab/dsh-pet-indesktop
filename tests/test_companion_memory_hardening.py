"""P1.1 privacy and explicit recall intent at real SQLite/chat boundaries."""
import json
import sqlite3
import pytest
from PySide6.QtWidgets import QApplication
from pet.companion.memory_extract import extract_memories, sensitive
from pet.companion.memory_store import MemoryStore
from pet.companion.memory_context import MemoryContext
from tests.test_companion_chat import send


PRIVATE_STATEMENTS = [
    '我的邮箱是fish@example.com',
    '我的电子邮箱是fish＠example．com',
    '我的工作是fish+test@example.com',
    '我的邮箱是fish [at] example [dot] com',
    '我的联系方式是fish@example.com',
    '我的电话是13800001234',
    '我的手机号码是138-0000-1234',
    '我的工作是联系+1 (202) 555-0147',
    '我的联系电话是010-12345678',
    '我的微信号是fish_friend',
    '我的QQ号是12345678',
    '我的家庭住址是北京市海淀区中关村大街27号',
    '我住在上海市浦东新区幸福小区三栋五零一室',
    '我的工作是住在123 Main Street',
    '我的邮政编码是100000',
    '我的真实姓名是某某某',
    '我的出生日期是1990-01-02',
    '我的收入是每月一万元',
    '我的护照号码是AB1234567',
    '我的病史是哮喘',
    '我喜欢https://example.com/private-profile',
    r'我的工作是C:\Users\fish\private.txt',
    '我的工作是/home/fish/private.txt',
    '我的邮箱是f\u200bish@example.com',
]


@pytest.mark.parametrize('statement', PRIVATE_STATEMENTS)
@pytest.mark.parametrize('explicit', [False, True])
def test_private_information_never_automatically_persisted(statement, explicit):
    text = ('请记住' if explicit else '') + statement
    assert extract_memories(text, True) == []


@pytest.mark.parametrize('statement', [
    '我喜欢密码学', '我喜欢tokenization', '我喜欢生日蛋糕',
    '我的工作是编程', '我的爱好是数据库', '我明天要看2026-10-12的展览',
    '请记住我住在上海', '我喜欢邮件写作',
])
def test_ordinary_preferences_and_coarse_city_not_misidentified(statement):
    assert not sensitive(statement)
    assert len(extract_memories(statement, True)) == 1


def seed(store):
    store.put('preference:color', '我喜欢蓝色', 'preference', 'explicit')
    store.put('preference:coffee', '我喜欢咖啡', 'preference', 'explicit')
    store.put('event:exam', '我下周要考试', 'event', 'explicit')
    store.put('fact:work', '我的工作是编程', 'fact', 'explicit')


@pytest.mark.parametrize('query', [
    '你还记得我以前告诉过你什么吗', '我之前跟你聊过哪些事',
    '你记得我说过什么吗？', '回忆一下我告诉过你的事情',
    '你记不记得我以前告诉过你什么', '帮我回想一下之前我和你聊过哪些事情',
])
def test_personal_recall_returns_bounded_known_facts(tmp_path, query):
    store = MemoryStore(tmp_path / 'm.db')
    seed(store)
    rows = store.search(query)
    assert {r.content for r in rows} == {r.content for r in store.list()}
    assert len(store.search(query, limit=2)) == 2
    assert sum(len(r.content) for r in store.search(query, char_limit=12)) <= 12


@pytest.mark.parametrize('query', [
    '我以前和你说过哪些喜好', '你还记得我的偏好吗', '我的兴趣爱好有哪些',
    '我有什么爱好', '以前我告诉过你我喜欢什么',
    '你知道我有哪些爱好吗', '你还记得我的偏好么', '你还记得我的那些兴趣吗',
])
def test_preference_overview_excludes_events_and_unrelated_facts(tmp_path, query):
    store = MemoryStore(tmp_path / 'm.db')
    seed(store)
    assert {r.content for r in store.search(query)} == {'我喜欢蓝色', '我喜欢咖啡'}


@pytest.mark.parametrize('query', ['你记得我喜欢什么色彩吗', '我以前说过什么颜色喜好', '你记得我的配色偏好吗'])
def test_specific_recall_does_not_expand_to_whole_database(tmp_path, query):
    store = MemoryStore(tmp_path / 'm.db')
    seed(store)
    assert [r.content for r in store.search(query)] == ['我喜欢蓝色']


@pytest.mark.parametrize('query', ['火星的颜色是什么', '你喜欢什么颜色', '以前的天气是什么样', '你以前告诉我哪些编程知识', '你知道火星的颜色吗'])
def test_unrelated_questions_do_not_pull_personal_memories(tmp_path, query):
    store = MemoryStore(tmp_path / 'm.db')
    seed(store)
    assert store.search(query) == []


def test_overview_limits_recent_safe_memories_and_manual_preferences(tmp_path):
    store = MemoryStore(tmp_path / 'm.db')
    for n in range(8):
        store.put(f'preference:{n}', f'我喜欢活动{n}', 'preference', 'explicit')
    store.put('manual:music', '我喜欢音乐', 'fact', 'manual')
    assert len(store.search('我以前和你说过哪些喜好', limit=999)) == 5
    assert store.search('我以前和你说过哪些喜好')[0].content == '我喜欢音乐'


def test_legacy_private_rows_are_visible_for_management_but_not_sent(tmp_path):
    store = MemoryStore(tmp_path / 'm.db')
    seed(store)
    # Simulate a record written by the P1 filter. Do not silently delete user data.
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE memories SET content=?,content_key=? WHERE topic='fact:work'", ('我的邮箱是fish@example.com', 'legacy-private'))
    assert any('@' in r.content for r in store.list())
    assert all('@' not in r.content for r in store.search('你记得我说过什么吗'))
    app = QApplication.instance() or QApplication([])
    provider = send(app, MemoryContext(store.path, '你记得我说过什么吗', True))
    assert 'fish@example.com' not in json.dumps(provider.requests[0], ensure_ascii=False)


def test_failed_private_manual_write_is_atomic(tmp_path):
    store = MemoryStore(tmp_path / 'm.db')
    seed(store)
    before = store.list()
    with pytest.raises(ValueError):
        store.put('private', '我的邮箱是fish@example.com')
    assert store.list() == before


def test_new_recall_respects_disabled_and_deleted_memory(tmp_path):
    app = QApplication.instance() or QApplication([])
    store = MemoryStore(tmp_path / 'm.db')
    seed(store)
    query = '我以前和你说过哪些喜好'
    disabled = send(app, MemoryContext(store.path, query, False))
    assert '我喜欢蓝色' not in json.dumps(disabled.requests[0], ensure_ascii=False)
    store.clear()
    enabled = send(app, MemoryContext(store.path, query, True))
    assert '我喜欢蓝色' not in json.dumps(enabled.requests[0], ensure_ascii=False)


@pytest.mark.parametrize('statement', [
    '我的Instagram账号是fish_private', '我的Telegram是fish_private',
    '我的社交帐号是fish_private', '我今年30岁',
    '我的联系方式是f i s h @ example . com',
    '我的工作是小明@例子.公司',
])
def test_additional_private_values_and_obfuscation(statement):
    assert extract_memories('请记住' + statement, True) == []


def test_contact_and_preference_sentences_are_not_merged(tmp_path):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / 'm.db'
    send(app, MemoryContext(path, '我的邮箱是fish@example.com。我喜欢蓝色。', True, True))
    assert [r.content for r in MemoryStore(path).list()] == ['我喜欢蓝色']


def test_explicit_no_recall_does_not_enumerate_private_rows(tmp_path, monkeypatch):
    store = MemoryStore(tmp_path / 'm.db')
    def forbidden():
        raise AssertionError('records should not be enumerated')
    monkeypatch.setattr(store, 'list', forbidden)
    assert store.search('不要读取我以前和你说过的喜好') == []


def test_bounded_overview_survives_process_restart_and_deletion(tmp_path):
    import subprocess
    import sys
    path = tmp_path / 'm.db'
    seed(MemoryStore(path))
    code = "from pet.companion.memory_store import MemoryStore;import sys;s=MemoryStore(sys.argv[1]);assert len(s.search('我以前和你说过哪些喜好'))==2;s.clear()"
    subprocess.run([sys.executable, '-c', code, str(path)], check=True, timeout=15)
    assert MemoryStore(path).search('你记得我说过什么吗') == []


@pytest.mark.parametrize('query', ['你还记得我叫什么吗', '你知道怎么称呼我吗'])
def test_name_synonyms_are_specific_not_a_general_overview(tmp_path, query):
    store = MemoryStore(tmp_path / 'm.db')
    seed(store)
    store.put('fact:name', '我叫小明', 'fact', 'explicit')
    assert [r.content for r in store.search(query)] == ['我叫小明']
