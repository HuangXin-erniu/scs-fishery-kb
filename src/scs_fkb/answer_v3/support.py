"""Claim-level support checks for cited answer sentences.

The model sometimes attaches a plausible document id to a sentence that the
cited chunk does not contain.  The audit calls this D7; this module gives the
answer path the same check so a bad citation is either corrected from the
evidence pack or the sentence is removed before the user sees it.
"""

from __future__ import annotations

import re
from typing import Any

CITATION_RE = re.compile(r"\[([A-Za-z0-9-]+)\s*§([^\]]+)\]")
SENTENCE_RE = re.compile(r"[^。！？；\n]+[。！？；]?")
NUMBER_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:万元|亿元|元|%|％|‰|天|个月|小时|公斤|千克|吨|海里|米|千瓦|年|月|日|条|款|项|倍|级)?"
)
SKIP_PREFIXES = ("缺口", "注意", "渠道", "时效", "口径", "版本", "未覆盖", "证据不足")
INFERENCE_PREFIXES = ("因此", "所以", "可见", "说明", "应核查", "不能仅凭", "这意味")


def sentences(text: str) -> list[str]:
    parts = [part.strip() for part in SENTENCE_RE.findall(text or "") if part.strip()]
    merged: list[str] = []
    for part in parts:
        if merged and re.fullmatch(r"(\[[^\]]+\]\s*)+", part):
            merged[-1] = merged[-1] + part
        else:
            merged.append(part)
    return merged


def _clean(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fff0-9A-Za-z%]", "", CITATION_RE.sub("", text or ""))


def _grams(text: str) -> set[str]:
    clean = _clean(text)
    if len(clean) < 2:
        return {clean} if clean else set()
    return {clean[index : index + 2] for index in range(len(clean) - 1)}


def _numbers(text: str) -> set[str]:
    return {match.group(0).replace(" ", "") for match in NUMBER_RE.finditer(text or "")}


CONTRADICTIONS = (
    ("一级", "二级"),
    ("二级", "一级"),
    ("禁止", "允许"),
    ("允许", "禁止"),
    ("可以", "不得"),
    ("不得", "可以"),
    ("必须", "无需"),
    ("无需", "必须"),
    ("有效", "无效"),
    ("无效", "有效"),
)


def _contradicts(claim: str, evidence: str) -> bool:
    return any(left in claim and right in evidence for left, right in CONTRADICTIONS)


def support_score(claim: str, evidence: str) -> float:
    """Containment of the claim's character bigrams in the evidence.

    A number in the claim that is absent from the evidence forces a zero: a
    paraphrased rule may still be supported, but an invented figure may not.
    A level or permission switch (一级/二级, 禁止/允许) is a contradiction, not a
    paraphrase.
    """
    if _contradicts(claim or "", evidence or ""):
        return 0.0
    claim_numbers = _numbers(CITATION_RE.sub("", claim or ""))
    if claim_numbers and not claim_numbers.issubset(_numbers(evidence)):
        return 0.0
    claim_grams = _grams(claim)
    if not claim_grams:
        return 0.0
    evidence_grams = _grams(evidence)
    return len(claim_grams & evidence_grams) / len(claim_grams)


def _labels(sentence: str) -> list[str]:
    return [f"{doc_id} §{section.strip()}" for doc_id, section in CITATION_RE.findall(sentence)]


def _best_item(claim: str, items: tuple[Any, ...]) -> tuple[Any | None, float]:
    best: Any | None = None
    best_score = 0.0
    for item in items:
        score = support_score(claim, item.quote or item.chunk.text)
        if score > best_score:
            best, best_score = item, score
    return best, best_score


def prune_unsupported(
    text: str,
    pack: Any,
    *,
    keep: float = 0.55,
    recite: float = 0.40,
) -> tuple[str, int]:
    """Re-cite or drop cited sentences that the cited chunk does not support.

    Returns the cleaned text and the number of dropped sentences.  Sentences
    without a citation, gap/caveat lines and scope notes are left untouched.
    """
    items = tuple(getattr(pack, "items", ()) or ())
    if not text or not items:
        return text, 0
    by_label = {item.label: item for item in items}
    kept: list[str] = []
    dropped = 0
    for sentence in sentences(text):
        if not sentence:
            continue
        if sentence.startswith(SKIP_PREFIXES):
            kept.append(sentence)
            continue
        if CITATION_RE.search(sentence) is None:
            if _numbers(sentence):
                dropped += 1
                continue
            kept.append(sentence)
            continue
        claim = CITATION_RE.sub("", sentence).strip()
        if len(_clean(claim)) < 6:
            dropped += 1
            continue
        if len(_clean(claim)) < 12:
            kept.append(sentence)
            continue
        cited = [by_label[label] for label in _labels(sentence) if label in by_label]
        best_cited = max(
            (support_score(claim, item.quote or item.chunk.text) for item in cited),
            default=0.0,
        )
        threshold = 0.75 if sentence.startswith(INFERENCE_PREFIXES) else keep
        if best_cited >= threshold:
            kept.append(sentence)
            continue
        best_item, best_score = _best_item(claim, items)
        if best_item is not None and best_score >= recite:
            kept.append(CITATION_RE.sub(f"[{best_item.label}]", sentence))
            continue
        dropped += 1
    cleaned = "\n".join(kept).strip()
    if dropped and cleaned:
        cleaned += f"\n缺口：已删除 {dropped} 句无证据支持的表述。"
    return cleaned, dropped
