"""Conservative local semantic labels; no embedding/model classification request."""
import json
import re
from .memory_extract import normalize
from .memory_retrieve import tokens

_PATTERNS = {'greeting': r'早安|早呀|早上好|午安|下午好|晚上好|晚安|你好|嗨',
             'drink': r'喝水|饮水|补水|水分|饮一|喝点水|喝口水',
             'break': r'久坐|起身|起来|休息|伸.*腰|活动.*身体|歇一|走一走'}


def text_key(text):
    return ''.join(c for c in normalize(text) if c.isalnum())


def classify(text, category=None):
    tags = {key for key, pattern in _PATTERNS.items() if re.search(pattern, text)}
    if category:
        tags.add(category)
    return tags


def repeats(text, recent, utc, semantic=True, category=None):
    key, wanted, tags = text_key(text), tokens(text_key(text)), classify(text, category)
    for row in recent:
        other = text_key(row['text'])
        if key == other or (len(min(key, other, key=len)) >= 8 and (key in other or other in key)):
            return True
        if semantic:
            parts = tokens(other)
            if wanted and len(wanted & parts)/max(1, len(wanted | parts)) >= .65:
                return True
            overlap = tags & set(json.loads(row['tags']))
            if any(utc-row['utc'] < (6*3600 if tag == 'greeting' else 2*3600) for tag in overlap):
                return True
    return False
