from __future__ import annotations

import re

from .contract import NumericAnchor

NUMBER_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(毫米|厘米|米|公里|海里|吨|公斤|千克|毫克|微克|升|立方米|元|万元|亿元|%|‰|天|个月|小时|年|月|日|时|艘|人|尾|倍|级|度|千瓦|马力)"
)
NUMERIC_QUESTION = re.compile(
    r"多少|几[个天年月日岁]?|多大|多长|多重|比例|限值|标准|尺寸|网目|幼鱼|规格|罚款|罚多少|金额|上限|下限|阈值|浓度|温度|产量"
)
BASIS_WORDS = {
    "全国": "全国口径",
    "南海": "南海海区",
    "海区": "海区口径",
    "分区": "分区口径",
    "年度": "年度值",
    "年均": "年均值",
    "单次": "单次值",
    "航次": "航次口径",
    "重量": "按重量计",
    "尾数": "按尾数计",
    "表": "表列值",
    "图": "图列值",
}


def is_numeric_question(question: str) -> bool:
    return bool(NUMERIC_QUESTION.search(question))


def extract(text: str, *, location: str = "") -> list[NumericAnchor]:
    """Extract number/unit pairs and the nearest basis word from a sentence."""
    anchors: list[NumericAnchor] = []
    for match in NUMBER_RE.finditer(text):
        window = text[max(0, match.start() - 18) : match.end() + 18]
        basis = next((label for word, label in BASIS_WORDS.items() if word in window), "")
        if not basis and location and re.search(r"表|附件|第\d+条", location):
            basis = "表列值" if "表" in location else "条款值"
        anchors.append(
            NumericAnchor(
                value=match.group(1),
                unit=match.group(2),
                basis=basis or "未标注口径",
                location=location,
            )
        )
    for _raw, rendered, _basis in render_pairs(text):
        value, unit = split_value_unit(rendered)
        if not value or not unit:
            continue
        if any(row.value == value and row.unit == unit for row in anchors):
            continue
        anchors.append(NumericAnchor(value=value, unit=unit, basis="未标注口径", location=location))
    return anchors


CN_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
CN_SMALL = {"十": 10, "百": 100, "千": 1000}
CN_BIG = {"万": 10000, "亿": 100000000}
CN_CHARS = "零〇一二三四五六七八九十百千万亿两"
UNIT_WORDS = (
    "毫米|厘米|公里|海里|千克|公斤|毫克|微克|立方米|万元|亿元|升|吨|米|克|元|"
    "%|‰|天|个月|小时|年|月|日|时|度|℃|艘|人|尾|倍|级|千瓦|马力"
)
CN_PERCENT_RE = re.compile(rf"百分之[{CN_CHARS}]+")
CN_VALUE_RE = re.compile(rf"([{CN_CHARS}]+)({UNIT_WORDS})")
LATIN_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mm|cm|km|kg|mg|μg|ug|m|t|%)\b")
UNIT_DECL_RE = re.compile(
    r"单位\s*[:：]\s*([\u4e00-\u9fa5%]{1,4})|（\s*(毫米|厘米|米|公斤|千克|吨|%)\s*）"
)
BARE_LINE_RE = re.compile(
    r"^(?P<prefix>[^。；，,]{0,40}?)(?P<op>[≥≤<>]\s*)?(?P<num>\d+(?:\.\d+)?)\s*$"
)
LATIN_UNIT_ALIASES = {
    "m": "米",
    "cm": "厘米",
    "mm": "毫米",
    "km": "公里",
    "kg": "kg",
    "mg": "mg",
    "t": "吨",
    "ug": "μg",
}
CN_UNIT_ALIASES = {"微克": "μg", "毫克": "mg", "克": "g", "千克": "kg"}


def cn_to_int(text: str) -> int | None:
    """Parse a Chinese numeral such as 二千, 十五, 一万二千 or 百分之二十."""
    if not text:
        return None
    if text.startswith("百分之"):
        text = text[3:]
    total = 0
    section = 0
    number = 0
    for char in text:
        if char in CN_DIGITS:
            number = CN_DIGITS[char]
        elif char in CN_SMALL:
            unit = CN_SMALL[char]
            if number == 0:
                number = 1
            section += number * unit
            number = 0
        elif char in CN_BIG:
            section += number
            if char == "万":
                total += section * 10000
            else:
                total = (total + section) * 100000000
            section = 0
            number = 0
        else:
            return None
    return total + section + number


def declared_unit(text: str) -> str:
    """Return the unit declared by a table header, if any."""
    match = UNIT_DECL_RE.search(text)
    if not match:
        return ""
    return match.group(1) or match.group(2) or ""


def _unit(value: int | float, unit: str) -> str:
    if unit == "%":
        return f"{value:g}%"
    if unit in {"万元", "亿元"}:
        return f"{value:g}{unit}"
    head, _, tail = unit.partition("/")
    head = CN_UNIT_ALIASES.get(head, head)
    if tail:
        tail = CN_UNIT_ALIASES.get(tail, tail)
        return f"{value:g}{head}/{tail}"
    return f"{value:g}{head}"


def render_pairs(text: str, unit_hint: str = "") -> list[tuple[str, str, str]]:
    """Return (original, rendered, basis) for faithful numeric renderings.

    The original wording is never replaced; callers append the rendering as a
    separate cited line. `unit_hint` is a table header unit used for bare values
    such as `肛长 ≥230` in a table that declares 单位:毫米.
    """
    pairs: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def add(original: str, rendered: str, basis: str) -> None:
        if rendered in seen or rendered == original:
            return
        seen.add(rendered)
        pairs.append((original, rendered, basis))

    for match in CN_PERCENT_RE.finditer(text):
        raw = match.group(0)
        value = cn_to_int(raw)
        if value is not None:
            add(raw, f"{value}%", f"原文：{raw}")
    for match in CN_VALUE_RE.finditer(text):
        raw = match.group(0)
        head = match.group(1)
        unit = match.group(2)
        if unit == "元" and head.endswith("万"):
            head, unit = head[:-1], "万元"
        elif unit == "元" and head.endswith("亿"):
            head, unit = head[:-1], "亿元"
        if head in {"千", "百"} and unit in {"克", "米"}:
            continue
        value = cn_to_int(head)
        rendered = _unit(value, unit) if value is not None else ""
        if rendered:
            add(raw, rendered, f"原文：{raw}")
    for match in LATIN_UNIT_RE.finditer(text):
        raw = match.group(0)
        alias = LATIN_UNIT_ALIASES.get(match.group(2), match.group(2))
        rendered = f"{match.group(1)}{alias}"
        add(raw, rendered, f"原文：{raw}")
    if unit_hint:
        for line in text.splitlines():
            stripped = " ".join(line.split())
            match = BARE_LINE_RE.match(stripped)
            if not match:
                continue
            prefix = match.group("prefix") or ""
            if re.search(r"[A-Za-z]|第|附件|表|图|注", prefix):
                continue
            number = match.group("num")
            add(stripped, f"{number}{unit_hint}", f"表列值，单位：{unit_hint}")
    return pairs


def split_value_unit(rendered: str) -> tuple[str, str]:
    """Split `2000公斤` into (`2000`, `公斤`) for NumericAnchor construction."""
    match = re.match(r"(\d+(?:\.\d+)?)(.*)", rendered)
    if not match:
        return "", ""
    return match.group(1), match.group(2)
