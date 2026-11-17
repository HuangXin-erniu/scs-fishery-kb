from __future__ import annotations

import re
from collections.abc import Iterable

SENTENCE_RE = re.compile(r"[^。！？；\n]+[。！？；]?")
NUMBER_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:万元|亿元|元|%|％|‰|天|个月|小时|公斤|千克|吨|海里|米|千瓦|年|月|日|条|款|项|倍|级)?"
)
CITATION_RE = re.compile(r"\[([A-Za-z0-9-]+)\s*§([^\]]+)\]")
PROVINCES = ("广西", "广东", "福建", "海南", "浙江", "山东", "江苏", "辽宁", "河北", "天津", "上海")


def sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_RE.findall(text or "") if part.strip()]


def ngrams(text: str, n: int = 3) -> set[str]:
    clean = re.sub(r"\s+", "", text or "")
    if len(clean) < n:
        return {clean} if clean else set()
    return {clean[i : i + n] for i in range(len(clean) - n + 1)}


def jaccard(a: str, b: str) -> float:
    left, right = ngrams(a), ngrams(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def numbers(text: str) -> set[str]:
    return {match.group(0).replace(" ", "") for match in NUMBER_RE.finditer(text or "")}


def citations(text: str) -> list[tuple[str, str]]:
    return [(match.group(1), match.group(2).strip()) for match in CITATION_RE.finditer(text or "")]


def entities(text: str) -> set[str]:
    found = {name for name in PROVINCES if name in (text or "")}
    if any(term in (text or "") for term in ("跟帮", "编组", "编队")):
        found.update({"编组", "跟帮"})
    for term in ("贝毒", "赤潮", "渔情", "补贴", "海龟", "玳瑁", "鲎", "带鱼"):
        if term in (text or ""):
            found.add(term)
    return found


def sentence_with_citation(text: str) -> Iterable[tuple[str, list[tuple[str, str]]]]:
    for sentence in sentences(text):
        yield sentence, citations(sentence)
