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


# Normalize confusable punctuation/invisible separators before inspecting values.
_INVISIBLE = re.compile(r'[\u200b-\u200f\u2060\ufeff]')
_EMAIL = re.compile(r"[\w.+%'-]+@[\w.-]+\.[^\W\d_]{2,63}", re.I)
_SECRET = re.compile(
    r'密码(?!学)|口令|密钥|身份证|银行卡|支付|病史|患有|诊断|护照|社保'
    r'|(?<![a-z0-9_])(?:api[ _-]?key|token|password|secret)(?![a-z0-9_])'
    r'|sk-[a-z0-9]|(?<!\d)\d{11,}(?!\d)', re.I)
_PRIVATE_FIELD = re.compile(
    r'(?:我的|我家(?:的)?|家庭|本人(?:的)?).{0,12}'
    r'(?:电子邮箱|邮箱|邮件地址|手机(?:号码)?|电话|联系(?:方式|人)?|住址|地址|微信(?:号)?|qq(?:号)?'
    r'|邮政编码|邮编|真实姓名|法定姓名|出生日期|生日(?:是|为)|年龄|收入|工资|经纬度|精确定位'
    r'|whatsapp|telegram|instagram|微博|社交账号|社交帐号|账号|帐号|账户)'
    r'|我(?:今年)?(?:\d{1,3}|[一二三四五六七八九十百]{1,5})岁'
    r'|(?:home|residential|mailing)\s+address'
    r'|(?:e-?mail|phone|mobile|wechat|qq)\s*(?:address|number|id)?\s*(?:is|:)', re.I)
_PHONE = re.compile(
    r'(?<!\d)(?:1[3-9](?:[ -]?\d){9}|\+\d[\d\s().-]{6,}\d|0\d{2,3}[- ]\d{7,8})(?!\d)')
_PRECISE_ADDRESS = re.compile(
    r'我(?:家住|住在|居住在|现住).{0,80}(?:区|县|村|镇|小区|公寓)'
    r'|(?:路|街|巷|弄).{0,20}[\d一二三四五六七八九十百零]+(?:号|栋|单元|室|楼)'
    r'|[\d一二三四五六七八九十百零]+(?:栋|单元|室|楼)'
    r'|(?<!\d)\d{1,6}\s+[a-z][a-z ]{0,60}\s(?:street|st|road|rd|avenue|ave|lane|ln)\b', re.I)
_PRIVATE_PATH = re.compile(r'https?://|ftp://|www\.|[a-z]:[\\/]|\\\\[^\s]+|/(?:home|users)/', re.I)


def sensitive(text):
    """Conservative private-value filter shared by extraction, storage and retrieval.

    This is a local heuristic, not a complete PII detector. Coarse city names,
    ordinary dates and technical interests are intentionally retained.
    """
    text = _INVISIBLE.sub('', unicodedata.normalize('NFKC', text))
    email_text = re.sub(r'\[(at|dot)\]|\((at|dot)\)',
                        lambda m: '@' if (m[1] or m[2]).lower() == 'at' else '.', text, flags=re.I)
    compact_email = re.sub(r'\s+', '', email_text)
    return bool(_EMAIL.search(compact_email) or _SECRET.search(text)
                or _PRIVATE_FIELD.search(text) or _PHONE.search(text)
                or _PRECISE_ADDRESS.search(text) or _PRIVATE_PATH.search(text))


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
