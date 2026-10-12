"""Bounded personal recall intent and small, auditable topic synonyms.

No model request, vector index or implicit full-history retrieval. Only explicit
personal overview questions may enumerate recent safe memories.
"""
import re
from .memory_extract import normalize

_ALIASES = {'preference:color': '颜色色彩配色色调', 'fact:name': '名字称呼姓名昵称'}
_FILLER = re.compile('|'.join(map(re.escape, sorted([
    '你还记得', '还记得', '你记不记得', '记不记得', '你记得', '你知道', '知道',
    '帮我回想一下', '回想一下', '回想', '回忆一下', '回忆', '记忆', '记得', '记住',
    '我的', '我以前', '我之前', '以前', '之前', '曾经', '过去', '长期',
    '告诉过', '告诉', '和你', '跟你', '说过', '聊过', '提过', '说',
    '有什么', '有哪些', '什么', '哪些事情', '哪些事', '哪些', '那些', '啥', '的事情', '事情', '的事', '一些',
    '喜好', '偏好', '兴趣', '爱好', '喜欢', '偏爱', '关于', '有关',
    '我', '你', '吗', '么', '呢', '的',
], key=len, reverse=True))))
_PREFERENCE = re.compile(r'^(?:我)?(?:最)?(?:不再喜欢|不喜欢|喜欢|偏爱)')


def recall_query(query):
    """Return scope (all/preferences/topic/none) and meaningful topic words."""
    query = normalize(query[:4000]).strip('？?，,：:')
    query = query.replace('叫什么', '名字').replace('怎么称呼', '名字')
    # Do not reinterpret a model's interests or generic factual question as the user's profile.
    if re.search(r'不要|不用|别(?:读取|回忆|提)|禁止', query):
        return 'none', ''
    if re.search(r'你.*(?:告诉|教过|说给).*我', query) and not re.search(r'我.*(?:告诉|说过|聊过).*你', query):
        return 'none', ''
    if '我' not in query and re.search(r'什么|哪些|为何|怎么|为什么|[?？]|[吗么呢]$', query):
        return 'none', ''
    personal = '我' in query
    recall = personal and bool(re.search(r'记得.*我|回忆.*我|我.*(?:告诉|说过|聊过|提过)|我的.*记忆', query))
    preferences = personal and bool(re.search(r'喜好|偏好|兴趣|爱好|喜欢|偏爱', query))
    topic = _FILLER.sub('', query).strip('？?，,：:。！!')
    if preferences and not topic:
        return 'preferences', ''
    if recall and not topic:
        return 'all', ''
    return ('preferences' if preferences else 'topic'), topic


def is_preference(row):
    # Hand-confirmed preferences in P1's manager were stored as kind=fact.
    return row.kind == 'preference' or (row.kind == 'fact' and bool(_PREFERENCE.match(row.content)))


def tokens(text):
    text = normalize(text)
    return (set(re.findall(r'[a-z0-9]+', text))
            | {text[i:i+2] for i in range(len(text)-1)
               if all('\u4e00' <= c <= '\u9fff' for c in text[i:i+2])})


def relevance(row, wanted):
    alias = _ALIASES.get(row.topic, '')
    if is_preference(row):
        if re.search(r'咖啡|茶|果汁|牛奶', row.content):
            alias += '饮料饮品爱喝喝口味'
        if re.search(r'吃|辣|甜|食物|菜', row.content):
            alias += '饮食食物口味'
    return len(wanted & tokens(row.content + alias))
