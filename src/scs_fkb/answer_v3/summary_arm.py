"""Model-written summary over the dump arm's clause set.

The dump arm already retrieves a large evidence pack. This module picks the
sections that can answer the question, lets the model compose a short summary
from exactly those sections, and then runs the same citation, number and support
checks the LLM answer arm uses. A draft that fails a check is repaired once and
otherwise dropped, so the caller falls back to the deterministic summary.

Nothing here changes the evidence text: the pack stays the dump arm's output.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ..llm import LLMClient, LLMError
from ..models import Chunk, SearchHit
from ..rag import LLMCache, _citations_from_text
from .llm_answer import (
    GAP_SENTENCE,
    _cached_json,
    _key,
    _label,
    _number_problems,
    _repair_messages,
    _resolve_citations,
    _sentence_problems,
    _sentences,
    _verify,
)
from .select import (
    BASIS,
    BODY,
    ENUM,
    MODAL,
    PROC,
    Clause,
    Slot,
    _grams,
    _idf,
    _lexical,
    _sections,
    _window,
    split_slots,
)

PROMPT_VERSION = "summary-model-v4"
MAX_SECTIONS = 8
MAX_WINDOW = 1500
MAX_EVIDENCE_CHARS = 11000
TYPE_PATTERNS = {"boolean": MODAL, "enum": ENUM, "procedure": PROC, "basis": BASIS, "body": BODY}
TYPE_BONUS = 0.05
LEADERS_PER_SLOT = 6
MAX_SUMMARY_CHARS = 900
MAX_POINTS = 2
GAP_LIMIT = 2

SUMMARY_SYSTEM = (
    "你是南海近海渔业知识库的摘要器，只能使用给出的证据清单，禁止外推。\n"
    "输出三部分：\n"
    "1. conclusion：一句话直接回答问题的第一问（数值、是否、期限、材料或受理层级），不要铺垫。\n"
    "2. points：0 到 2 句，回答其余的每一问；每句只讲一件事。\n"
    "3. gaps：证据清单确实没有覆盖的部分，写成“缺什么”，最多两条；都覆盖了就给空数组。\n"
    "4. coverage：三档，按“证据里有没有一句能写进结论的话”判断。\n"
    "   - full：问题问到的每一项都有条款。\n"
    "   - partial：至少有一句能直接写进 conclusion（哪怕只是一个定义、一条原则、一个办理主体），"
    "但关键数值、具体程序或分级标准缺失。此时必须填 partial：把能写的那句写进 conclusion，"
    "缺的写进 gaps。**缺具体数值、缺具体程序、缺分级标准都不是 none。**\n"
    "   - none：所有候选段落都与问题无关，一句都用不上；此时 conclusion 写成“证据未覆盖……”。\n"
    "硬性要求：每个陈述句都必须带引用，格式 [DOC_ID §章节]，必须与证据清单里的标签完全一致；"
    "数字必须逐字来自证据并带单位；证据没有的数值不要写；不要写“根据证据”之类的空话。\n"
    '只输出 JSON：{"conclusion": "……", "points": ["……"], "gaps": ["……"], "coverage": "full"}'
)

CITATION_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_.-]*)\s*§([^\]]+)\]")


@dataclass(frozen=True)
class SummaryDraft:
    """A verified model summary; never returned unless every check passed."""

    conclusion: str
    points: tuple[str, ...]
    gaps: tuple[str, ...]
    citations: tuple[Any, ...]
    repaired: bool = False
    coverage: str = "full"

    @property
    def answerable(self) -> bool:
        return self.coverage != "none"

    def text(self) -> str:
        return " ".join([self.conclusion, *self.points])


def _section_score(values: dict[int, float]) -> float:
    """Rank a section by its best clause; the next two only break ties, once per clause."""
    top = sorted(values.values(), reverse=True)
    return round(top[0] + 0.001 * sum(top[1:3]), 6)


def _section_hits(question: str, clauses: Sequence[Clause]) -> list[SearchHit]:
    """Rank sections by the questions they can answer, then keep the best ones."""
    if not clauses:
        return []
    idf = _idf(clauses)
    default = math.log(len(clauses) + 1) + 1.0
    # A section is ranked by its single best clause. Summing the three best clauses
    # made long articles beat short exact ones: the give-way rule is one clause,
    # while the stand-on article has several, so the exact rule never reached the
    # shortlist. The next two clauses only break ties, at one-thousandth of their
    # weight, so a section whose several clauses all match slightly outranks a tie
    # without letting breadth substitute for precision.
    buckets: dict[tuple[str, str], dict[int, float]] = {}
    for slot in split_slots(question):
        relaxed = Slot(text=slot.text, kind="text", unit=slot.unit)
        pattern = TYPE_PATTERNS.get(slot.kind)
        for value, clause in _lexical(relaxed, clauses, _grams(slot.text), idf, default):
            if pattern is not None and pattern.search(clause.text):
                value = round(value + TYPE_BONUS, 6)
            key = (clause.doc_id, clause.section)
            per_clause = buckets.setdefault(key, {})
            current = per_clause.get(id(clause))
            if current is None or value > current:
                per_clause[id(clause)] = value
    ranked = [
        (_section_score(values), doc_id, section) for (doc_id, section), values in buckets.items()
    ]
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    ordered: list[tuple[str, str, list[Clause]]] = []
    seen: set[tuple[str, str]] = set()
    by_key = {(doc, section): items for doc, section, items in _sections(clauses)}
    for _score, doc_id, section in ranked:
        key = (doc_id, section)
        if key in seen or key not in by_key:
            continue
        seen.add(key)
        ordered.append((doc_id, section, by_key[key]))
        if len(ordered) >= MAX_SECTIONS:
            break
    hits: list[SearchHit] = []
    for doc_id, section, items in ordered:
        text = _window(items, MAX_WINDOW)
        if not text.strip():
            continue
        chunk = Chunk(
            chunk_id=f"{doc_id}|{section}"[:80],
            doc_id=doc_id,
            source_id=items[0].chunk_id or "section",
            page=items[0].page,
            section=section,
            text=text,
            token_count=len(text),
            char_start=0,
            char_end=len(text),
            sensitivity="public",
            source_class=items[0].source_class,
        )
        hits.append(SearchHit(chunk=chunk, score=1.0))
    return hits


def _render(hits: Sequence[SearchHit]) -> tuple[str, dict[str, Any]]:
    """Render the section windows with the same labels the verifiers expect."""
    parts: list[str] = []
    by_label: dict[str, Any] = {}
    used = 0
    for hit in hits:
        block = f"[{_label(hit.chunk)}] {' '.join(hit.chunk.text.split())}"
        if used + len(block) > MAX_EVIDENCE_CHARS:
            break
        parts.append(block)
        by_label[_label(hit.chunk)] = hit
        used += len(block)
    return "\n\n".join(parts), by_label


def _clean(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit].strip()


def _points(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = [str(item) for item in value]
    else:
        items = []
    cleaned = [_clean(item, 300) for item in items if _clean(item, 300)]
    return tuple(cleaned[:MAX_POINTS])


def _gaps(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = [str(item) for item in value]
    else:
        items = []
    cleaned = [_clean(item, 120) for item in items if _clean(item, 120)]
    return tuple(cleaned[:GAP_LIMIT])


def _checks(text: str, by_label: dict[str, Any], hits: list[Any]) -> list[str]:
    problems = _sentence_problems(text, by_label, allow_gap=True, allow_next_citation=True)
    problems += _number_problems(text, by_label)
    valid, invalid = _resolve_citations(text, hits)
    if not valid:
        problems += [f"unresolved:{item}" for item in invalid]
    return problems


def _request(client: LLMClient, cache: LLMCache | None, question: str, context: str) -> dict:
    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM},
        {
            "role": "user",
            "content": f"问题：\n{question}\n\n证据清单：\n{context}\n\n按 JSON 输出。",
        },
    ]
    return _cached_json(
        cache,
        _key(PROMPT_VERSION, question, context, client.config.model),
        client,
        messages,
        max_tokens=2500,
    )


def _repair(
    client: LLMClient,
    cache: LLMCache | None,
    question: str,
    context: str,
    text: str,
    problems: list[str],
) -> str:
    messages = _repair_messages(question, context, text, problems)
    try:
        value = _cached_json(
            cache,
            _key(PROMPT_VERSION + ":repair", question, context + text, client.config.model),
            client,
            messages,
            max_tokens=2000,
        )
    except LLMError:
        return ""
    return _clean(value.get("answer"), MAX_SUMMARY_CHARS)


def _coverage_of(value: dict[str, Any]) -> str:
    """Read the three-level coverage, tolerating an older boolean reply."""
    raw = str(value.get("coverage") or "").strip().lower()
    if raw in {"full", "partial", "none"}:
        return raw
    answerable = value.get("answerable")
    if answerable is False:
        return "none"
    return "full"


def _mark(diagnostics: dict[str, Any] | None, stage: str, detail: str = "") -> None:
    """Record why a draft was dropped, so the next round measures instead of guessing."""
    if diagnostics is None:
        return
    diagnostics["stage"] = stage
    if detail:
        diagnostics["detail"] = detail


def summarize(
    question: str,
    clauses: Sequence[Clause],
    client: LLMClient | None,
    cache: LLMCache | None = None,
    *,
    diagnostics: dict[str, Any] | None = None,
) -> SummaryDraft | None:
    """Return a verified draft, or None so the caller keeps the deterministic summary."""
    if client is None:
        _mark(diagnostics, "no_client")
        return None
    if not clauses:
        _mark(diagnostics, "no_clauses")
        return None
    hits = _section_hits(question, clauses)
    if not hits:
        _mark(diagnostics, "no_sections")
        return None
    context, by_label = _render(hits)
    if not context:
        _mark(diagnostics, "no_context")
        return None
    try:
        value = _request(client, cache, question, context)
    except LLMError as exc:
        _mark(diagnostics, "llm_error", str(exc)[:120])
        return None
    if value.get("abstained") is True:
        _mark(diagnostics, "abstained")
        return None
    coverage = _coverage_of(value)
    conclusion = _clean(value.get("conclusion"), 400)
    points = _points(value.get("points"))
    gaps = _gaps(value.get("gaps"))
    if not conclusion:
        if coverage == "none":
            _mark(diagnostics, "not_answerable")
            return SummaryDraft(
                conclusion="已登记语料未覆盖该问题",
                points=(),
                gaps=gaps,
                citations=(),
                coverage="none",
            )
        _mark(diagnostics, "empty_conclusion")
        return None
    text = " ".join([conclusion, *points])
    if len(text) > MAX_SUMMARY_CHARS:
        _mark(diagnostics, "too_long", str(len(text)))
        return None
    problems = _checks(text, by_label, hits)
    repaired = False
    if problems:
        fixed = _repair(client, cache, question, context, text, problems)
        if not fixed:
            _mark(diagnostics, "repair_empty", problems[0])
            return None
        repaired = True
        text = fixed
        conclusion, points = _resplit(text, points)
        if not conclusion:
            _mark(diagnostics, "repair_empty_conclusion")
            return None
        problems = _checks(text, by_label, hits)
        if problems:
            _mark(diagnostics, "checks", problems[0])
            return None
    citations = tuple(_citations_from_text(text, hits))
    sentences = [item for item in _sentences(text) if len(item.strip()) >= 4]
    gap_only = bool(sentences) and all(GAP_SENTENCE.search(item) for item in sentences)
    if coverage == "none" and (points or not gap_only):
        # Bullet points or a non-gap conclusion mean the draft did use the evidence,
        # so the question is at least partly covered whatever the flag says.
        coverage = "partial"
    if coverage == "partial" and not gaps:
        # Partial coverage without a declared gap is indistinguishable from a full answer.
        coverage = "full"
    if gap_only:
        # Nothing to verify: the draft says the evidence does not cover the question.
        _mark(diagnostics, "gap_only")
        return SummaryDraft(
            conclusion=conclusion,
            points=points,
            gaps=gaps,
            citations=(),
            repaired=repaired,
            coverage=coverage,
        )
    if not citations:
        _mark(diagnostics, "citations")
        return None
    supported, reason = _verify(question, text, by_label, client, cache)
    if not supported:
        fixed = _repair(client, cache, question, context, text, ["结论未被所引证据支持"])
        if not fixed:
            _mark(diagnostics, "verify_repair_empty", reason[:80])
            return None
        text = fixed
        conclusion, points = _resplit(text, points)
        if not conclusion or _checks(text, by_label, hits):
            _mark(diagnostics, "verify_checks", reason[:80])
            return None
        supported, reason = _verify(question, text, by_label, client, cache)
        if not supported:
            _mark(diagnostics, "verify", reason[:80])
            return None
        citations = tuple(_citations_from_text(text, hits))
        if not citations:
            _mark(diagnostics, "citations_after_repair")
            return None
        repaired = True
    _mark(diagnostics, "ok")
    return SummaryDraft(
        conclusion=conclusion,
        points=points,
        gaps=gaps,
        citations=citations,
        repaired=repaired,
        coverage=coverage,
    )


def _resplit(text: str, fallback_points: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    """Rebuild conclusion and points from a repaired single-string answer."""
    sentences = [item.strip() for item in re.split(r"(?<=[。！？；])", text) if item.strip()]
    if not sentences:
        return "", fallback_points
    return sentences[0], tuple(sentences[1 : 1 + MAX_POINTS])


__all__ = ["SummaryDraft", "summarize", "PROMPT_VERSION"]
