"""Query-aware clause selection for the user-facing summary.

The dump arm quotes a large evidence pack. This module decides which single
clause answers each part of the question, so the summary can answer instead of
showing an adjacent article. Everything here is deterministic: the lexical path
needs no model, and the optional cross-encoder only reorders candidates that the
lexical pass already admitted.

The selector never invents text. A selection is a clause that already exists in
the pack, optionally tightened to a window that is still a verbatim substring.
When no clause satisfies a slot, the slot yields a gap instead of a neighbour.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .numbers import NUMBER_RE

NUMERIC_Q = re.compile(
    r"多少|几(?:个|年|天|月|号|位|米|条|艘|成|倍)|多大|多长|多重|比例|限额|金额|罚款|罚多少"
    r"|处罚|上限|下限|标准是多少"
)
TIME_Q = re.compile(r"什么时候|何时|哪天|哪年|几月|几号|起止|截止|到期|期限|有效期|多久|多长时间")
BOOL_Q = re.compile(
    r"能不能|可不可以|算不算|是不是|要不要|有没有|够不够|需不需要|行不行|准不准|让不让"
    r"|还能|可否|能否|不算"
)
BODY_Q = re.compile(r"找谁|哪个部门|去哪|向谁|谁来管|谁负责|哪个单位|县里|省里|市里|窗口")
ENUM_Q = re.compile(r"哪些|什么材料|要交|需要什么|清单|几位|包括|目录|条件|资料")
PROC_Q = re.compile(r"怎么办|怎么申请|怎么办理|流程|程序|手续|如何申请|怎么弄")
BASIS_Q = re.compile(r"哪条|第几条|依据|根据什么|按什么规定|什么法|哪部")

CN_NUM = re.compile(
    r"[零〇一二三四五六七八九十百千万两]+(?:年|个月|月|日|天|小时|元|万元|吨|海里|米|毫米|厘米|%|级|艘|人|次|倍|个)"
)
DATE = re.compile(
    r"\d{4}\s*年|\d{1,2}\s*月\s*\d{1,2}\s*日|\d{1,2}\s*月|自.{0,12}至|起止|截止|以前|之前|之后|有效期"
)
MODAL = re.compile(r"可以|不得|应当|允许|禁止|除外|无需|不需|必须|不能|能够|属于|不属于|一律")
ENUM = re.compile(
    r"[（(][一二三四五六七八九十][）)]|、[^。]{2,}、|材料|证件|证明|提交|包括|清单|目录|条件|资料"
)
PROC = re.compile(r"申请|提交|受理|审核|审批|发放|办理|程序|流程|期限|工作日|备案")
BASIS = re.compile(r"第[一二三四五六七八九十百零〇\d]+条")
BODY = re.compile(r"主管部门|人民政府|负责|受理|海警|市场监管|人民法院|法院|窗口|县级以上")
UNIT = re.compile(r"个月|工作日|海里|毫米|厘米|万元|年|月|日|天|小时|元|吨|米|%|级|艘|人|次|倍")

NORMATIVE = {"normative", "standard"}
STOP_GRAMS = {
    "什么",
    "怎么",
    "多少",
    "可以",
    "不能",
    "能不",
    "是不",
    "不是",
    "要不",
    "不要",
    "有没",
    "没有",
    "够不",
    "需不",
    "行不",
    "准不",
    "让不",
    "哪条",
    "哪年",
    "哪天",
    "哪些",
    "几位",
    "多久",
    "多长",
    "多大",
    "时候",
    "么时",
    "么办",
    "么申",
    "这些",
    "那些",
    "我们",
    "自己",
}
KINDS = ("numeric", "time", "boolean", "enum", "procedure", "basis", "body", "text")
SHAPE_PENALTY = re.compile(r"目录|附录|附表|附件|参考文献|作者简介|年版|年第")
DEFAULT_RERANK_MODEL = "BAAI/bge-reranker-v2-m3-int8"


@dataclass(frozen=True)
class Clause:
    text: str
    doc_id: str
    section: str = ""
    page: int = 0
    rank: int = 0
    source_class: str = ""
    chunk_id: str = ""

    def label(self) -> str:
        where = f"§{self.section}" if self.section else f"p.{self.page}"
        return f"[{self.doc_id} {where}]"

    def rendered(self) -> str:
        return f"{self.text} {self.label()}"


@dataclass(frozen=True)
class Slot:
    text: str
    kind: str = "text"
    unit: str = ""


@dataclass(frozen=True)
class Selection:
    slot: Slot
    clause: Clause | None = None
    score: float = 0.0
    reason: str = "ok"

    @property
    def answered(self) -> bool:
        return self.clause is not None

    def render(self) -> str:
        return self.clause.rendered() if self.clause is not None else ""


def _setting(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def _enabled(name: str, default: str) -> bool:
    return _setting(name, default).lower() in {"on", "1", "true", "yes"}


def _clean(fragment: str) -> str:
    text = fragment.strip(" ，,。.、：:；;\t\n")
    return text.strip()


def split_slots(question: str, *, max_slots: int = 3) -> tuple[Slot, ...]:
    """Split the question on question marks and semicolons, then type each part."""
    parts = [_clean(item) for item in re.split(r"[？?；;]+", question)]
    parts = [item for item in parts if len(item) >= 4]
    if not parts:
        parts = [_clean(question)] if _clean(question) else [question]
    slots = tuple(_slot_of(item) for item in parts[:max_slots])
    return slots or (Slot(text=question),)


def _slot_of(text: str) -> Slot:
    for kind, pattern in (
        ("basis", BASIS_Q),
        ("boolean", BOOL_Q),
        ("body", BODY_Q),
        ("time", TIME_Q),
        ("numeric", NUMERIC_Q),
        ("enum", ENUM_Q),
        ("procedure", PROC_Q),
    ):
        if pattern.search(text):
            unit = ""
            if kind in {"numeric", "time"}:
                match = UNIT.search(text)
                unit = match.group(0) if match else ""
            return Slot(text=text, kind=kind, unit=unit)
    return Slot(text=text, kind="text")


def slot_kind(text: str) -> str:
    return _slot_of(text).kind


def _grams(text: str) -> set[str]:
    clean = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", text)
    return {clean[index : index + 2] for index in range(max(0, len(clean) - 1))}


def _has_number(text: str) -> bool:
    return bool(NUMBER_RE.search(text) or CN_NUM.search(text))


def _passes(slot: Slot, text: str) -> bool:
    if slot.kind == "numeric":
        if not _has_number(text):
            return False
        return not slot.unit or slot.unit in text
    if slot.kind == "time":
        return bool(DATE.search(text))
    if slot.kind == "boolean":
        return bool(MODAL.search(text))
    if slot.kind == "enum":
        return bool(ENUM.search(text))
    if slot.kind == "procedure":
        return bool(PROC.search(text))
    if slot.kind == "basis":
        return bool(BASIS.search(text))
    if slot.kind == "body":
        return bool(BODY.search(text))
    return True


def _idf(clauses: Sequence[Clause]) -> dict[str, float]:
    total = len(clauses) or 1
    df: dict[str, int] = {}
    for clause in clauses:
        for gram in _grams(clause.text):
            df[gram] = df.get(gram, 0) + 1
    return {gram: math.log((total + 1) / (count + 1)) + 1.0 for gram, count in df.items()}


def _coverage(
    grams: set[str], clause_grams: set[str], idf: dict[str, float], default: float
) -> float:
    if not grams:
        return 0.0
    wanted = 0.0
    hits = 0.0
    for gram in grams:
        weight = idf.get(gram, default)
        wanted += weight
        if gram in clause_grams:
            hits += weight
    return hits / wanted if wanted else 0.0


def _lexical(
    slot: Slot,
    clauses: Sequence[Clause],
    grams: set[str],
    idf: dict[str, float],
    default: float,
) -> list[tuple[float, Clause]]:
    scored: list[tuple[float, Clause]] = []
    total = max(1, len(clauses))
    for clause in clauses:
        if not _passes(slot, clause.text):
            continue
        value = _coverage(grams, _grams(clause.text), idf, default)
        if clause.source_class in NORMATIVE:
            value += 0.06
        elif clause.source_class == "official_statistics":
            value += 0.03
        value += 0.08 * (1.0 - min(1.0, clause.rank / total))
        if len(clause.text) > 320:
            value -= 0.10
        if SHAPE_PENALTY.search(clause.text):
            value -= 0.08
        scored.append((round(value, 6), clause))
    scored.sort(key=lambda item: (-item[0], item[1].doc_id, item[1].section, item[1].text))
    return scored


def _reranker() -> Any:
    key = "_scs_fkb_summary_reranker"
    cached = getattr(_reranker, key, None)
    if cached is not None:
        return cached
    try:
        from ..retrieve_v2.rerank import Reranker

        model = _setting("SCS_FKB_SUMMARY_RERANK_MODEL", DEFAULT_RERANK_MODEL)
        cache = _setting("SCS_FKB_SUMMARY_RERANK_CACHE", "")
        if not cache:
            root = _setting("SCS_FKB_DATA_ROOT", "")
            cache = str(Path(root) / "embeddings" / "models") if root else ""
        cached = Reranker(model_name=model, cache_dir=cache or None)
    except Exception:  # noqa: BLE001 - optional local model
        cached = None
    setattr(_reranker, key, cached)
    return cached


def _rerank_scores(question: str, candidates: Sequence[Clause]) -> list[float] | None:
    reranker = _reranker()
    if reranker is None:
        return None
    try:
        scores = reranker.score_pairs(question, [clause.text[:200] for clause in candidates])
    except Exception:  # noqa: BLE001 - model missing or backend failure
        return None
    values = [float(value) for value in scores]
    if len(values) != len(candidates):
        return None
    return values


def _normalize(values: Sequence[float]) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high - low < 1e-9:
        return [0.5 for _ in values]
    return [(value - low) / (high - low) for value in values]


def _sections(clauses: Sequence[Clause]) -> list[tuple[str, str, list[Clause]]]:
    """Group clauses by their section; the section is the unit a reader checks."""
    groups: dict[tuple[str, str], list[Clause]] = {}
    for clause in clauses:
        groups.setdefault((clause.doc_id, clause.section), []).append(clause)
    return [
        (doc_id, section, sorted(items, key=lambda item: item.rank))
        for (doc_id, section), items in groups.items()
    ]


def _window(items: Sequence[Clause], limit: int = 600) -> str:
    parts: list[str] = []
    used = 0
    for item in items:
        text = item.text.strip()
        if not text:
            continue
        if used + len(text) > limit:
            break
        parts.append(text)
        used += len(text) + 1
    return " ".join(parts)


def _enumerators(items: Sequence[Clause]) -> list[Clause]:
    """Consecutive ``（一）（二）`` items belong to the same list."""
    pattern = re.compile(r"^[（(][一二三四五六七八九十][）)]")
    return [item for item in items if pattern.match(item.text.strip())]


def _merge_items(items: Sequence[Clause], chosen: Clause, limit: int) -> Clause:
    """Merge the enumerator run around ``chosen`` into one quote."""
    run = _enumerators(items)
    if len(run) < 2 or chosen not in run:
        return chosen
    index = run.index(chosen)
    start = max(0, index - 1)
    merged = [run[start].text.strip()]
    used = len(merged[0])
    for item in run[start + 1 :]:
        text = item.text.strip()
        if used + len(text) + 1 > limit:
            break
        merged.append(text)
        used += len(text) + 1
    if len(merged) < 2:
        return chosen
    return Clause(
        text=" ".join(merged),
        doc_id=chosen.doc_id,
        section=chosen.section,
        page=chosen.page,
        rank=chosen.rank,
        source_class=chosen.source_class,
        chunk_id=chosen.chunk_id,
    )


PICKER_VERSION = "summary-picker-v1"
PICKER_SYSTEM = (
    "你是条款定位器。给定一个渔民问题和若干编号的条款段落，选出**能直接回答该问题**的那一段。\n"
    "只按段落文字判断，不要用外部知识；如果所有段落都没有直接答案，选 0。\n"
    '只输出 JSON：{"choice": 编号}'
)


def llm_picker(client: Any, cache: Any) -> Any:
    """Return a callable that picks one numbered window, or 0 for none.

    The picker is a closed-set choice: it can only return an index that the
    caller already retrieved, so a wrong pick can never introduce new text.
    """

    from ..llm import LLMError, parse_json_object

    def pick(question: str, options: Sequence[str]) -> int:
        if len(options) < 2:
            return 1 if options else 0
        payload = "\n".join(f"[{index}] {text}" for index, text in enumerate(options, start=1))
        key = None
        if cache is not None:
            digest = hashlib.sha256(
                f"{PICKER_VERSION}\n{question}\n{payload}\n{client.config.model}".encode()
            ).hexdigest()
            key = f"pick-{digest[:24]}.json"
            cached = cache.get(key)
            if isinstance(cached, dict) and "choice" in cached:
                return _choice(cached.get("choice"), len(options))
        messages = [
            {"role": "system", "content": PICKER_SYSTEM},
            {"role": "user", "content": f"问题：{question}\n\n段落：\n{payload}\n\n按 JSON 输出。"},
        ]
        try:
            value = parse_json_object(client.chat(messages, max_tokens=200))
        except LLMError:
            return 0
        choice = _choice(value.get("choice"), len(options))
        if cache is not None and key is not None:
            cache.put(key, {"choice": choice})
        return choice

    return pick


def _choice(value: Any, size: int) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return 0
    return number if 0 <= number <= size else 0


def _tighten(text: str, grams: set[str], limit: int) -> str:
    if len(text) <= limit:
        return text
    step = max(4, limit // 8)
    best_start = 0
    best_score = -1
    for start in range(0, max(1, len(text) - limit + 1), step):
        window = text[start : start + limit]
        score = sum(1 for gram in grams if gram in window)
        if score > best_score:
            best_score = score
            best_start = start
    window = text[best_start : best_start + limit]
    tail = max(window.rfind(mark) for mark in "。；，")
    if tail >= limit * 0.6:
        window = window[: tail + 1]
    return window.strip()


def select_slots(
    question: str,
    clauses: Sequence[Clause],
    *,
    max_slots: int | None = None,
    min_score: float | None = None,
    rerank: bool | None = None,
    rerank_top: int | None = None,
    quote_chars: int | None = None,
    picker: Any = None,
) -> tuple[Selection, ...]:
    """Pick one clause per slot, or a gap when no candidate qualifies."""
    limit_slots = (
        max_slots if max_slots is not None else int(_setting("SCS_FKB_SUMMARY_MAX_SLOTS", "3"))
    )
    floor = (
        min_score if min_score is not None else float(_setting("SCS_FKB_SUMMARY_MIN_SCORE", "0.12"))
    )
    use_rerank = rerank if rerank is not None else _enabled("SCS_FKB_SUMMARY_RERANK", "on")
    top = (
        rerank_top if rerank_top is not None else int(_setting("SCS_FKB_SUMMARY_RERANK_TOP", "36"))
    )
    quote = (
        quote_chars
        if quote_chars is not None
        else int(_setting("SCS_FKB_SUMMARY_QUOTE_CHARS", "160"))
    )
    if not clauses:
        return ()
    idf = _idf(clauses)
    default = math.log(len(clauses) + 1) + 1.0
    selections: list[Selection] = []
    seen: set[tuple[str, str, str]] = set()
    for slot in split_slots(question, max_slots=limit_slots):
        grams = _grams(slot.text)
        scored = [
            (value, clause)
            for value, clause in _lexical(slot, clauses, grams, idf, default)
            if value > 0
        ]
        if not scored:
            selections.append(Selection(slot=slot, reason="no_candidate"))
            continue
        head = scored[: max(1, top)]
        sections = _sections([clause for _value, clause in head])
        ranked: list[tuple[float, str, str, list[Clause]]] = []
        for doc_id, section, items in sections:
            section_score = max(
                (
                    value
                    for value, clause in scored
                    if clause.doc_id == doc_id and clause.section == section
                ),
                default=0.0,
            )
            ranked.append((section_score, doc_id, section, items))
        ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
        section_pick = ranked[0]
        shortlist = ranked[:8]
        if picker is not None:
            windows = [_window(items) for _score, _doc, _section, items in shortlist]
            try:
                choice = int(picker(slot.text, windows))
            except Exception:  # noqa: BLE001 - a picker failure must not break the answer
                choice = 0
            if 1 <= choice <= len(shortlist):
                section_pick = shortlist[choice - 1]
            elif choice == 0 and ranked[0][0] < max(floor, 0.25):
                selections.append(
                    Selection(slot=slot, score=round(ranked[0][0], 4), reason="picker_none")
                )
                continue
        elif use_rerank and len(ranked) > 1:
            shortlist = ranked[:8]
            windows = [_window(items) for _score, _doc, _section, items in shortlist]
            scores = _rerank_scores(slot.text, windows)
            if scores is not None:
                blended = _normalize(scores)
                pick = max(
                    range(len(shortlist)),
                    key=lambda index: (
                        round(
                            0.55 * blended[index] + 0.45 * max(0.0, min(1.0, shortlist[index][0])),
                            4,
                        ),
                        -index,
                    ),
                )
                section_pick = shortlist[pick]
        best_score = round(section_pick[0], 4)
        in_section = [
            (value, clause)
            for value, clause in scored
            if clause.doc_id == section_pick[1] and clause.section == section_pick[2]
        ]
        in_section.sort(key=lambda item: (-item[0], item[1].rank, item[1].text))
        best_clause = in_section[0][1]
        if slot.kind == "enum":
            best_clause = _merge_items(section_pick[3], best_clause, 240)
        if best_score < floor:
            selections.append(Selection(slot=slot, score=best_score, reason="low_score"))
            continue
        key = (best_clause.doc_id, best_clause.section, best_clause.text)
        if key in seen and selections:
            selections.append(
                Selection(slot=slot, clause=best_clause, score=best_score, reason="duplicate")
            )
            continue
        seen.add(key)
        text = _tighten(best_clause.text, grams, quote)
        clause = (
            best_clause
            if text == best_clause.text
            else Clause(
                text=text,
                doc_id=best_clause.doc_id,
                section=best_clause.section,
                page=best_clause.page,
                rank=best_clause.rank,
                source_class=best_clause.source_class,
                chunk_id=best_clause.chunk_id,
            )
        )
        selections.append(Selection(slot=slot, clause=clause, score=best_score, reason="ok"))
    return tuple(selections)


def gaps_of(selections: Iterable[Selection]) -> tuple[str, ...]:
    """Return the human-readable gap line for every slot that was not answered."""
    lines: list[str] = []
    for item in selections:
        if item.answered:
            continue
        what = item.slot.text.strip(" ？?。")
        lines.append(f"{what}：已登记语料未找到直接规定")
    return tuple(lines)


__all__ = [
    "Clause",
    "Selection",
    "Slot",
    "gaps_of",
    "select_slots",
    "slot_kind",
    "split_slots",
]
