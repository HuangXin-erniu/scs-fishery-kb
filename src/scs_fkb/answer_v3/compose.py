from __future__ import annotations

import os
import re
from dataclasses import replace
from typing import Any

from .asof import detect as detect_asof
from .asof import fallback as fallback_asof
from .channels import ChannelBook
from .contract import AnswerContract, Channel, SlotView
from .numbers import extract as extract_numbers
from .numbers import is_numeric_question
from .scope import out_of_scope
from .select import gaps_of, select_slots

FALLBACK_NOTE = "未能生成结论（摘要校验未通过，见依据摘录）"

SENTENCE_RE = re.compile(r"(?<=[。！？；])|\n+")
CITATION_RE = re.compile(r"\[[A-Za-z0-9][^\]]*\]")
CONDITION_WORDS = ("应当", "须", "不得", "除外", "限于", "适用", "按照", "符合", "禁止")
BOILERPLATE_RE = re.compile(
    r"附件|目录|附录|见表|年第\s*期|—\s*\d+\s*—|公告|通告|令|办法（|办法\(|公布|印发|通知"
)
TIME_INTENT_RE = re.compile(r"什么时候|何时|几月|几号|起始|起止|开始|结束|期限|到期|有效期")
QUESTION_STOP = set("的了是在和与或及对对于这那个什么怎样如何多少几")


def _citation_only(part: str) -> bool:
    return bool(CITATION_RE.search(part)) and not CITATION_RE.sub("", part).strip(" 。；，：\n")


def _sentences(text: str) -> list[str]:
    merged: list[str] = []
    for part in (item.strip() for item in SENTENCE_RE.split(text)):
        if not part:
            continue
        if merged and _citation_only(part):
            merged[-1] = f"{merged[-1]} {part}"
        else:
            merged.append(part)
    return merged


def _bigrams(text: str) -> set[str]:
    clean = re.sub(r"\s+", "", text)
    return {clean[index : index + 2] for index in range(max(0, len(clean) - 1))}


def _score(sentence: str, question_grams: set[str]) -> int:
    grams = _bigrams(CITATION_RE.sub("", sentence))
    return len(grams & question_grams)


def _pick_conclusion(sentences: list[str], question: str, *, numeric: bool = False) -> str:
    cited = [
        item
        for item in sentences
        if CITATION_RE.search(item) and len(CITATION_RE.sub("", item).strip(" 。；，")) >= 6
    ]
    if not cited:
        return ""
    grams = _bigrams(question)
    numeric_intent = numeric or bool(TIME_INTENT_RE.search(question))

    def weight(item: tuple[int, str]) -> tuple[int, int]:
        index, sentence = item
        score = _score(sentence, grams)
        if numeric_intent and re.search(r"\d", sentence):
            score += 2
        if BOILERPLATE_RE.search(sentence):
            score -= 3
        return (score, -index)

    return max(enumerate(cited), key=weight)[1]


def _basis_for(basis: str, section: str) -> str:
    if basis and basis != "未标注口径":
        return basis
    if "表" in section:
        return "表列值（条款）"
    if section:
        return f"{section}（条款）"
    return "未标注口径"


def _pick_conditions(sentences: list[str], conclusion: str) -> tuple[str, ...]:
    picked: list[str] = []
    for sentence in sentences:
        if sentence == conclusion or not CITATION_RE.search(sentence):
            continue
        if any(word in sentence for word in CONDITION_WORDS):
            picked.append(sentence)
        if len(picked) >= 2:
            break
    return tuple(picked)


def _view_of(sentence: str) -> SlotView:
    match = re.search(r"\[([A-Za-z0-9][^\]]*?)\s*§([^\]]+)\]", sentence)
    return SlotView(
        text=sentence,
        doc_id=match.group(1).strip() if match else "",
        section=match.group(2).strip() if match else "",
        kind="model",
    )


def _selector_on() -> bool:
    return os.environ.get("SCS_FKB_SUMMARY_SELECT", "off").strip().lower() in {
        "on",
        "1",
        "true",
        "yes",
    }


def _slot_view(
    question: str, clauses: Any, picker: Any = None
) -> tuple[tuple[SlotView, ...], tuple[str, ...]]:
    selections = select_slots(question, clauses, picker=picker)
    answered = [item for item in selections if item.answered]
    slots = tuple(
        SlotView(
            text=item.render(),
            doc_id=item.clause.doc_id if item.clause else "",
            section=item.clause.section if item.clause else "",
            kind=item.slot.kind,
            score=item.score,
        )
        for item in answered
    )
    return slots, gaps_of(selections)


def _body(
    *,
    answerability: str,
    conclusion: str,
    conditions: tuple[str, ...],
    points: tuple[str, ...] = (),
    as_of_line: str,
    numbers_line: str,
    gap: tuple[str, ...],
    channels: tuple[Channel, ...],
    evidence: str,
) -> str:
    lines: list[str] = []
    if conclusion:
        lines.append(f"结论：{conclusion}")
    else:
        lines.append("结论：无法从已登记语料给出结论。")
    lines.extend(f"要点：{item}" for item in points)
    if conditions:
        lines.append("适用条件：" + "；".join(conditions))
    if as_of_line:
        lines.append(f"版本：{as_of_line}")
    if numbers_line:
        lines.append(f"数值与口径：{numbers_line}")
    if gap:
        lines.append("缺口：" + "；".join(gap))
    if channels:
        lines.append("渠道：" + "；".join(f"{item.name}，{item.hint}" for item in channels))
    if evidence:
        lines.append("依据摘录：")
        lines.append(evidence)
    return "\n".join(lines)


def compose(
    question: str,
    answer_text: str,
    *,
    doc_ids: list[str],
    registry: dict[str, dict[str, Any]],
    channels: ChannelBook,
    clauses: Any = (),
    picker: Any = None,
    draft: Any = None,
    draft_status: str = "",
) -> AnswerContract:
    """Build the contract-shaped answer from the deterministic evidence pack."""
    summary_source = "model" if draft is not None else (draft_status or "deterministic")
    scoped, scope_reason = out_of_scope(question)
    if scoped:
        gap, channel = channels.resolve(question, scope=True)
        return AnswerContract(
            answerability="abstain",
            conclusion="",
            summary_source="deterministic",
            gap=(scope_reason,),
            channel=channel,
            body=_body(
                answerability="abstain",
                conclusion="",
                conditions=(),
                as_of_line="",
                numbers_line="",
                gap=(scope_reason,),
                channels=channel,
                evidence="",
            ),
        )

    numeric = is_numeric_question(question)
    slots: tuple[SlotView, ...] = ()
    slot_gaps: tuple[str, ...] = ()
    points: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    fell_back = draft is None and draft_status == "fallback"
    if draft is not None:
        slots = tuple(
            _view_of(item) for item in [draft.conclusion, *draft.points] if str(item).strip()
        )
        slot_gaps = tuple(draft.gaps)
    elif not fell_back and clauses and _selector_on():
        slots, slot_gaps = _slot_view(question, clauses, picker)
    if slots:
        conclusion = slots[0].text
        points = tuple(item.text for item in slots[1:])
    elif fell_back:
        # A dropped draft must not leave raw OCR text in the conclusion slot.
        conclusion = FALLBACK_NOTE
        points = ()
        conditions = ()
    else:
        sentences = _sentences(answer_text)
        conclusion = _pick_conclusion(sentences, question, numeric=numeric)
        conditions = _pick_conditions(sentences, conclusion) if conclusion else ()
    if not doc_ids or not answer_text.strip():
        gap, channel = channels.resolve(question)
        fallback_line = fallback_asof(question)
        return AnswerContract(
            answerability="abstain",
            conclusion="",
            summary_source="deterministic",
            gap=(gap, "已登记语料中没有可支撑该问题的依据"),
            channel=channel,
            body=_body(
                answerability="abstain",
                conclusion="",
                conditions=(),
                as_of_line=fallback_line,
                numbers_line="",
                gap=(gap, "已登记语料中没有可支撑该问题的依据"),
                channels=channel,
                evidence="",
            ),
        )

    order = ([slots[0].doc_id] if slots else []) + list(doc_ids)
    as_of = detect_asof(question, order, registry)
    anchors = extract_numbers(" ".join([conclusion, *points, *conditions])) or extract_numbers(
        answer_text
    )
    section = slots[0].section if slots else ""
    if not section:
        match = re.search(r"§([^\]]+)", answer_text)
        if match:
            section = match.group(1).strip()
    anchors = [replace(anchor, basis=_basis_for(anchor.basis, section)) for anchor in anchors]
    unique_anchors: list[Any] = []
    seen_anchors: set[tuple[str, str]] = set()
    for anchor in anchors:
        key = (anchor.value, anchor.unit)
        if key in seen_anchors:
            continue
        seen_anchors.add(key)
        unique_anchors.append(anchor)
    anchors = unique_anchors
    gap: list[str] = list(slot_gaps)
    if fell_back:
        gap.append("摘要未通过校验，未生成结论；原文见依据摘录")
    if numeric and not anchors and "缺少可核数值或口径" not in gap:
        gap.append("缺少可核数值或口径")

    answerability = "partial" if fell_back else "answerable"
    if not conclusion:
        answerability = "partial"
        gap.append("证据不足以形成结论")
    elif gap:
        answerability = "partial"

    channel: tuple[Channel, ...] = ()
    if gap:
        resolved_gap, channel = channels.resolve(question)
        if not slot_gaps and not any(item.startswith("缺少可核数值") for item in gap):
            gap.insert(0, resolved_gap)

    gap = list(dict.fromkeys(gap))
    numbers_line = "；".join(f"{item.value}{item.unit}（{item.basis}）" for item in anchors[:4])
    as_of_line = as_of.declared if as_of else ""
    body = _body(
        answerability=answerability,
        conclusion=conclusion,
        conditions=conditions,
        points=points,
        as_of_line=as_of_line,
        numbers_line=numbers_line,
        gap=tuple(gap),
        channels=channel,
        evidence=answer_text,
    )
    return AnswerContract(
        answerability=answerability,
        conclusion=conclusion,
        conditions=conditions,
        gap=tuple(gap),
        channel=channel,
        as_of=as_of,
        numbers=tuple(anchors),
        slots=slots,
        body=body,
        summary_source=summary_source,
    )
