"""Conservative local extraction: only first-person statements, never model replies.

No extra API call, inferred facts, transcript copies or sensitive auto memories.
Unrecognized phrasing is left for manual management rather than guessed.
"""
from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class Candidate:
    topic: str
    content: str
    kind: str
    source: str


def normalize(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).casefold().strip('。.!！')


def sensitive(text):
    return bool(re.search(r'密码|口令|密钥|api.?key|token|身份证|银行卡|支付|病史|患有|诊断|password|secret|sk-[a-z0-9]|\b\d{11,}\b', text, re.I))


def extract_memories(text: str, automatic: bool = False) -> list[Candidate]:
    result = []
    # A small, documented grammar is deliberately safer than guessing with an LLM.
    for sentence in re.split(r'[。！!\n]', text[:4000])[:20]:
        sentence = sentence.strip()
        explicit = bool(re.match(r'^(?:请)?(?:记住|记得)(?:：|:)?', sentence))
        if not explicit and not automatic:
            continue
        content = re.sub(r'^(?:请)?(?:记住|记得)(?:：|:)?', '', sentence).strip()
        if (not content or len(content) > 240 or sensitive(content)
                or re.search(r'可能|也许|如果|假如|听说|似乎|猜|不确定|是不是|是否|[?？“”"`]|吗$', content)):
            continue
        topic = None
        kind = 'fact'
        like = re.fullmatch(r'我(?:最)?(?:不再喜欢|不喜欢|喜欢|偏爱)([^，,；;：:]+)', content)
        attribute = re.fullmatch(r'我的([^，,；;：:]{1,20})(?:是|为)([^，,；;]+)', content)
        name = re.fullmatch(r'我(?:叫|的名字是)([^，,；;]{1,30})', content)
        event = re.fullmatch(r'我(?:今天|明天|后天|下周|下个月|今年|最近|正在)(?:要|将|准备|在)?([^，,；;]+)', content)
        if like:
            kind = 'preference'
            value = like[1]
            topic = 'preference:color' if re.fullmatch(r'(?:蓝|红|绿|黄|紫|黑|白|粉|橙|灰|青)(?:色)?', value) else 'preference:' + normalize(value)
        elif attribute:
            topic = 'fact:' + normalize(attribute[1])
        elif name:
            topic = 'fact:name'
        elif event:
            kind, topic = 'event', 'event:' + normalize(event[1])
        elif explicit and re.fullmatch(r'我(?:有|住在|在|是)[^，,；;：:]+', content):
            topic = 'fact:' + normalize(content)
        if topic:
            result.append(Candidate(topic, content, kind, 'explicit' if explicit else 'statement'))
    return result[:5]
