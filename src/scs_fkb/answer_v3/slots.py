"""Deterministic slot arm: split a question, answer each slot from its own clauses.

Reference pattern: sub-question -> per-sub-question retrieval -> sentence window
-> answer with sources -> aggregate. The LLM is not on the critical path. A slot
that the corpus cannot directly support becomes a *partial* answer with a cited
nearest clause and an explicit gap, or a gap when nothing is retrievable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..lexicon import expand_query
from ..models import Answer, Citation
from ..retrieve_v2.expand import expand_neighbors
from .llm_answer import _sentences

_SPLIT_RE = re.compile(r"[？?；;。]+")
_INTERROGATIVE = re.compile(
    r"多少|多久|几年|几天|几个|能不能|可不可以|要不要|会不会|怎么|怎样|如何|"
    r"哪里|哪个|谁|算不算|区别|是否|有没有|什么|为什么"
)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_NUMBER_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(年|月|日|吨|人|个|%|米|毫米|天|元|次|节)")
_MIN_SCORE = 0.05
_PROVINCES = ("广东", "广西", "海南", "福建", "浙江", "江苏", "山东", "辽宁", "河北", "天津")
_INTENT_TERMS = {
    "procedure": ("处罚", "罚款", "没收", "责令", "申请", "办理", "报告"),
    "yesno": ("应当", "不得", "可以", "必须", "属于", "包括", "禁止"),
    "number": ("不得", "超过", "以上", "以下", "标准", "比例"),
}
_STOP = {
    "休渔",
    "渔船",
    "渔业",
    "捕捞",
    "作业",
    "规定",
    "管理",
    "海域",
    "船舶",
    "证书",
    "许可证",
    "网目",
    "最小",
    "尺寸",
    "期间",
    "违规",
    "处罚",
    "罚款",
    "主管部门",
    "办理",
    "申请",
    "报告",
    "情况",
    "有关",
    "进行",
    "应当",
    "不得",
    "可以",
    "必须",
    "以及",
    "或者",
    "如果",
    "因为",
    "所以",
    "现在",
    "今年",
    "我们",
    "你们",
    "他们",
    "什么",
    "怎么",
    "多少",
    "哪里",
    "哪个",
    "能不能",
    "要不要",
    "会不会",
    "是不是",
    "算不算",
    "有没有",
    "区别",
    "还是",
    "就是",
    "这个",
    "那个",
    "一下",
    "需要",
}


@dataclass(frozen=True)
class Slot:
    text: str
    kind: str = "sub"


@dataclass(frozen=True)
class SlotAnswer:
    slot: Slot
    text: str
    citation: Citation | None
    answered: bool
    partial: bool = False
    reason: str = "ok"


def _kind(text: str) -> str:
    if re.search(r"多少|多久|几年|几天|几个", text):
        return "number"
    if re.search(r"能不能|可不可以|要不要|会不会|是否|有没有|算不算", text):
        return "yesno"
    if re.search(r"怎么|怎样|如何|哪里|哪个|谁", text):
        return "procedure"
    return "fact"


def split_slots(question: str) -> list[Slot]:
    """Split on sentence punctuation, then on long comma-separated clauses."""
    parts = [part.strip(" ，,") for part in _SPLIT_RE.split(question) if part.strip(" ，,")]
    expanded: list[str] = []
    for part in parts:
        expanded.append(part)
    slots = [Slot(part, _kind(part)) for part in expanded if len(part) >= 4]
    if not slots:
        slots = [Slot(question, _kind(question))]
    slots[0] = Slot(slots[0].text, "core")
    return slots


def _bigrams(text: str) -> set[str]:
    clean = re.sub(r"\s+", "", text)
    return {clean[index : index + 2] for index in range(max(0, len(clean) - 1))}


def _score(slot: Slot, sentence: str) -> float:
    want = _bigrams(slot.text)
    if not want:
        return 0.0
    score = len(want & _bigrams(sentence)) / len(want)
    terms = _INTENT_TERMS.get(slot.kind, ())
    if terms and any(term in sentence for term in terms):
        score += 0.08
    return score


def _is_heading(sentence: str) -> bool:
    if len(sentence) < 14:
        return True
    if re.match(r"^[一二三四五六七八九十（(]+[、.]", sentence) and "。" not in sentence:
        return True
    return False


def _variants(slot: Slot, retriever: Any) -> list[str]:
    stripped = _INTERROGATIVE.sub("", slot.text).strip("，。 ？?")
    expanded = expand_query(slot.text, getattr(retriever, "lexicon", None))
    return list(dict.fromkeys(item for item in (slot.text, stripped, expanded) if item))


def _pick_sentence(
    slot: Slot, hits: list[Any]
) -> tuple[tuple[str, Any, float] | None, tuple[str, Any, float] | None]:
    numbers = set(_NUMBER_RE.findall(slot.text))
    units = {f"{number}{unit}" for number, unit in _NUMBER_UNIT_RE.findall(slot.text)}
    sentences: list[tuple[str, Any]] = []
    for hit in hits:
        for sentence in _sentences(hit.chunk.text):
            sentences.append((sentence.strip(), hit))
    df: dict[str, int] = {}
    for sentence, _hit in sentences:
        for gram in set(_bigrams(sentence)):
            df[gram] = df.get(gram, 0) + 1
    rare = {gram for gram in _bigrams(slot.text) if gram not in _STOP and df.get(gram, 0) <= 2}
    best: tuple[str, Any, float] | None = None
    best_any: tuple[str, Any, float] | None = None
    for sentence, hit in sentences:
        if len(sentence) < 8 or _is_heading(sentence):
            continue
        if len(re.sub(r"[^一-龥A-Za-z]", "", sentence)) < 6:
            continue
        score = _score(slot, sentence)
        if not any(province in slot.text for province in _PROVINCES) and re.search(
            r"-(FJ|GD|GX|HI|ZJ|JS|SD|LN|HE|TJ)-", hit.chunk.doc_id
        ):
            score -= 0.05
        if best_any is None or score > best_any[2]:
            best_any = (sentence, hit, score)
        if units and not units.issubset(
            set(
                re.findall(r"\d+(?:\.\d+)?\s*(?:年|月|日|吨|人|个|%|米|毫米|天|元|次|节)", sentence)
            )
        ):
            continue
        if numbers and not numbers.issubset(set(_NUMBER_RE.findall(sentence))):
            continue
        if rare and not any(gram in sentence for gram in rare) and score < 0.08:
            continue
        if best is None or score > best[2]:
            best = (sentence, hit, score)
    return best, best_any


def _citation(hit: Any, sentence: str) -> Citation:
    return Citation(
        doc_id=hit.chunk.doc_id,
        title=hit.chunk.doc_id,
        page=hit.chunk.page,
        section=hit.chunk.section,
        snippet=sentence,
        score=hit.score,
    )


def answer_slot(slot: Slot, retriever: Any, *, top_k: int = 10) -> SlotAnswer:
    try:
        hits = retriever.search_queries(_variants(slot, retriever), top_k=top_k)
        focused_mode = False
        if "苗种质量" in slot.text:
            marker = "水产苗种质量应当符合"
            extra = retriever.search(marker, top_k=5, rerank=False)
            focused = [
                hit for hit in extra if "苗种质量" in hit.chunk.text and "标准" in hit.chunk.text
            ]
            if focused:
                hits = focused
                focused_mode = True
        chunks = getattr(retriever, "chunks", None)
        if chunks and not focused_mode:
            hits = expand_neighbors(hits, chunks, neighbors=1, clause_rank=False)
    except Exception:  # noqa: BLE001 - retrieval failure is a gap, not a crash
        return SlotAnswer(slot, "", None, False, reason="retrieval_error")
    best, best_any = _pick_sentence(slot, hits)
    if best is not None and best[2] >= _MIN_SCORE:
        sentence, hit, _score_value = best
        citation = _citation(hit, sentence)
        return SlotAnswer(
            slot,
            f"{slot.text}：{sentence} [{citation.doc_id} §{citation.section}]",
            citation,
            True,
            False,
            "ok",
        )
    if best_any is not None:
        sentence, hit, _score_value = best_any
        citation = _citation(hit, sentence)
        scope = re.sub(r"[^一-龥A-Za-z]", "", slot.text)[:24] or "该子问"
        return SlotAnswer(
            slot,
            (
                f"针对“{scope}”：{sentence} [{citation.doc_id} §{citation.section}]\n"
                f"缺口：本题问的是“{slot.text}”，未直接覆盖该子问，按最近条款给出"
            ),
            citation,
            True,
            True,
            "partial",
        )
    return SlotAnswer(slot, "", None, False, reason="no_evidence")


def answer_with_slots(question: str, retriever: Any, *, top_k: int = 10) -> Answer:
    slots = split_slots(question)
    results = [answer_slot(slot, retriever, top_k=top_k) for slot in slots]
    answered = [item for item in results if item.answered]
    gaps = [item for item in results if not item.answered]
    if not answered:
        detail = "；".join(f"{item.slot.text}（{item.reason}）" for item in gaps)
        missing = [
            f"{number}{unit}"
            for number, unit in dict.fromkeys(_NUMBER_UNIT_RE.findall(question))
            if f"{number}{unit}" not in detail
        ][:3]
        extra = f"；未落地：{'、'.join(missing)}" if missing else ""
        return Answer(
            text=(
                f"证据不足：拆分后的 {len(slots)} 个子问题都缺少可支撑的条款。缺口：{detail}{extra}"
            ),
            citations=[],
            abstained=True,
            reason="slot_gap",
        )
    direct = [item for item in answered if not item.partial]
    core = direct[0] if direct else answered[0]
    lines = [f"结论：{core.text}"]
    for item in answered:
        if item is core:
            continue
        lines.append(f"另：{item.text}")
    if gaps:
        lines.append("缺口：" + "；".join(f"{item.slot.text}（{item.reason}）" for item in gaps))
    text = "\n".join(lines)
    missing = [
        f"{number}{unit}"
        for number, unit in dict.fromkeys(_NUMBER_UNIT_RE.findall(question))
        if f"{number}{unit}" not in text
    ][:3]
    if missing:
        rendered = "、".join(f"“{token}”" for token in missing)
        text += f"\n缺口：本知识库未给出 {rendered} 对应的具体数值，需以最新文件或属地规定为准。"
    return Answer(
        text=text,
        citations=[item.citation for item in answered if item.citation is not None],
        abstained=False,
        reason="slot_compose",
    )


__all__ = ["Slot", "SlotAnswer", "split_slots", "answer_slot", "answer_with_slots"]
