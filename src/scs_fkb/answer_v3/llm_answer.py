"""LLM composition arm: grounded answers with citation, number and support checks."""

from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from typing import Any

from ..llm import LLMClient, LLMError, parse_json_object
from ..models import Answer
from ..rag import CITATION_RE, LLMCache, _citations_from_text

PROMPT_VERSION = "contract-v2"
MAX_HITS = 8
MAX_EVIDENCE_CHARS = 7000
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9._-])\d+(?:\.\d+)?(?![A-Za-z0-9._-])")
NUMBER_UNIT_RE = re.compile(
    r"(?<![A-Za-z0-9._-])(\d+(?:\.\d+)?)\s*"
    r"(万元|亿元|元|%|‰|毫米|厘米|米|公里|海里|吨|公斤|千克|克|天|个月|年|月|日|时|小时|人|艘|千瓦|马力)?"
)
MULTIPLIER = {"万元": 10000.0, "亿元": 100000000.0}
UNIT_CLASS = {
    "元": "money",
    "万元": "money",
    "亿元": "money",
    "%": "pct",
    "‰": "permille",
}
SECTION_HINT = re.compile(r"(第[一二三四五六七八九十百零〇\d]{1,6}条)")
SENTENCE_SPLIT = re.compile(r"(?<=[。！？；])|\n+")

ANSWER_SYSTEM = (
    "你是南海近海渔业知识库的作答器，只能使用下面给出的证据，禁止使用外部知识。\n"
    "输出要求：\n"
    "1. 第一句给结论：直接回答问到的数值、是否、时限或办理路径，不要先铺垫。\n"
    "2. 结论之后给适用条件与例外；涉及办理的写清受理层级和材料。\n"
    "3. 每个事实句都必须带引用，格式 [DOC_ID §章节] 或 [DOC_ID p.页码]，"
    "DOC_ID、章节、页码必须与证据清单完全一致。\n"
    "4. 数字必须逐字来自证据原文，并带单位；证据给出海区、年度或表列口径时，"
    "在数字后用括号写口径。\n"
    "5. 证据只覆盖部分子问题时，先回答已覆盖的部分并给出引用，再用一句缺口说明缺什么；"
    "只有完全找不到相关条款时才 abstained=true，并在 reason 写明缺什么。\n"
    '只输出 JSON：{"abstained": false, "answer": "……", "reason": "ok"}'
)

REPAIR_SYSTEM = (
    "你在修复一份带引用的渔业答复。下面列出未被证据支持的数字或缺少引用的句子。\n"
    "只做两件事：删掉证据不支持的数字，或把它改成证据中的原值；给缺引用的句子补上"
    "正确的 [DOC_ID §章节] 或 [DOC_ID p.页码]。不得引入新事实。\n"
    '只输出 JSON：{"abstained": false, "answer": "……", "reason": "ok"}'
)

VERIFY_SYSTEM = (
    "你是引用核验器。给定问题、答案和答案引用的证据，判断：\n"
    "a) 每个结论是否被所引证据支持；b) 答案中的数字是否与证据一致；"
    "c) 是否存在证据没有覆盖的推断。\n"
    '只输出 JSON：{"supported": true/false, "reason": "简短理由"}'
)


class LLMAnswerError(RuntimeError):
    """Raised when the model reply cannot be used as a contract answer."""


def _key(kind: str, question: str, context: str, model: str) -> str:
    digest = hashlib.sha256(f"{kind}\n{question}\n{context}\n{model}".encode()).hexdigest()
    return f"contract-{digest[:24]}.json"


def _cached_json(
    cache: LLMCache | None,
    key: str,
    client: LLMClient,
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
) -> dict:
    if cache is not None:
        cached = cache.get(key)
        if cached is not None:
            return cached
    value = parse_json_object(client.chat(messages, max_tokens=max_tokens))
    if cache is not None:
        cache.put(key, value)
    return value


def _label(chunk: Any) -> str:
    section = f" §{chunk.section}" if chunk.section else ""
    page = f" p.{chunk.page}" if getattr(chunk, "page", 0) else ""
    return f"{chunk.doc_id}{section}{page}"


def _enrich(hits: list[Any]) -> list[Any]:
    """Give section-less chunks an honest in-memory label so citations resolve."""
    enriched: list[Any] = []
    for hit in hits:
        chunk = hit.chunk
        if not chunk.section.strip():
            match = SECTION_HINT.search(chunk.text[:80])
            label = match.group(1) if match else f"p.{chunk.page}"
            chunk = replace(chunk, section=label)
            hit = replace(hit, chunk=chunk)
        enriched.append(hit)
    return enriched


def _evidence(hits: list[Any]) -> tuple[str, dict[str, Any]]:
    """Render the evidence pack and index it by citation label."""
    parts: list[str] = []
    by_label: dict[str, Any] = {}
    used = 0
    for hit in hits[:MAX_HITS]:
        chunk = hit.chunk
        text = " ".join(chunk.text.split())
        block = f"[{_label(chunk)}] {text}"
        if used + len(block) > MAX_EVIDENCE_CHARS:
            break
        parts.append(block)
        by_label[_label(chunk)] = hit
        used += len(block)
    return "\n\n".join(parts), by_label


def _sentences(text: str) -> list[str]:
    merged: list[str] = []
    for part in (item.strip() for item in SENTENCE_SPLIT.split(text)):
        if not part:
            continue
        citation_only = CITATION_RE.search(part) and not CITATION_RE.sub("", part).strip(
            " 。；，：\n"
        )
        if merged and citation_only:
            merged[-1] = f"{merged[-1]} {part}"
        else:
            merged.append(part)
    return merged


def _citation_labels(text: str) -> list[str]:
    return [
        f"{doc}{(' §' + section) if section else ''}"
        for doc, _page, section in CITATION_RE.findall(text)
    ]


def _cited_hits(text: str, by_label: dict[str, Any]) -> list[Any]:
    found: list[Any] = []
    for doc_id, page, section in CITATION_RE.findall(text):
        for hit in by_label.values():
            chunk = hit.chunk
            if chunk.doc_id != doc_id:
                continue
            if page and chunk.page != int(page):
                continue
            if section and not chunk.section.startswith(section):
                continue
            if hit not in found:
                found.append(hit)
    return found


def _sentence_problems(text: str, by_label: dict[str, Any]) -> list[str]:
    """Sentences that state facts without a resolvable citation."""
    problems: list[str] = []
    for sentence in _sentences(text):
        if len(sentence) < 8:
            continue
        if not CITATION_RE.search(sentence):
            problems.append(f"uncited:{sentence[:24]}")
    return problems


def _values(text: str) -> set[tuple[str, float]]:
    """Normalised (unit class, value) pairs, so 1 万元 matches 10000 元."""
    values: set[tuple[str, float]] = set()
    for match in NUMBER_UNIT_RE.finditer(text):
        value = float(match.group(1))
        unit = match.group(2) or ""
        if unit in MULTIPLIER:
            value *= MULTIPLIER[unit]
        classes = UNIT_CLASS.get(unit, unit or "num")
        values.add((classes, round(value, 4)))
    return values


def _grounded(value: tuple[str, float], evidence: set[tuple[str, float]]) -> bool:
    cls, number = value
    for other_cls, other in evidence:
        if other_cls != cls:
            continue
        if abs(number - other) <= max(0.01, abs(other) * 0.005):
            return True
    return False


def _number_problems(text: str, by_label: dict[str, Any]) -> list[str]:
    """Numbers in a cited sentence that do not appear in the cited evidence."""
    problems: list[str] = []
    for sentence in _sentences(text):
        cited = _cited_hits(sentence, by_label)
        if not cited:
            continue
        evidence: set[tuple[str, float]] = set()
        for hit in cited:
            evidence |= _values(" ".join(hit.chunk.text.split()))
        answer_values = _values(sentence)
        for cls, value in answer_values:
            if not _grounded((cls, value), evidence):
                problems.append(f"ungrounded:{value:g}")
    return problems


def _resolve_citations(text: str, hits: list[Any]) -> tuple[bool, list[str]]:
    """A citation resolves when it names a retrieved document and, if given, a page or section."""
    invalid: list[str] = []
    for doc_id, page, section in CITATION_RE.findall(text):
        candidates = [hit for hit in hits if hit.chunk.doc_id == doc_id]
        if page:
            candidates = [hit for hit in candidates if hit.chunk.page == int(page)]
        if section:
            candidates = [
                hit for hit in candidates if hit.chunk.section.startswith(section.strip())
            ]
        if not candidates:
            invalid.append(
                f"{doc_id}{(' p.' + page) if page else ''}{(' §' + section) if section else ''}"
            )
    return not invalid, invalid


def _abstain(reason: str) -> Answer:
    return Answer(
        text="证据不足：现有证据无法支持回答，已按缺口处理。",
        abstained=True,
        reason=reason,
    )


def _answer_messages(question: str, context: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": ANSWER_SYSTEM},
        {
            "role": "user",
            "content": (
                f"问题（请回答所有子问题）：\n{question}\n\n证据清单：\n{context}\n\n按 JSON 输出。"
            ),
        },
    ]


def _repair_messages(
    question: str, context: str, answer: str, problems: list[str]
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": REPAIR_SYSTEM},
        {
            "role": "user",
            "content": (
                f"问题：\n{question}\n\n证据清单：\n{context}\n\n"
                f"待修复答案：\n{answer}\n\n问题清单：{'；'.join(problems[:6])}\n\n"
                "按 JSON 输出修复后的答案。"
            ),
        },
    ]


def _verify(
    question: str,
    answer: str,
    by_label: dict[str, Any],
    client: LLMClient,
    cache: LLMCache | None,
) -> tuple[bool, str]:
    cited = _cited_hits(answer, by_label)
    if not cited:
        return False, "no_cited_evidence"
    context = "\n\n".join(
        f"[{_label(hit.chunk)}] {' '.join(hit.chunk.text.split())}" for hit in cited
    )
    messages = [
        {"role": "system", "content": VERIFY_SYSTEM},
        {
            "role": "user",
            "content": (
                f"问题：\n{question}\n\n答案：\n{answer}\n\n被引证据：\n{context}\n\n按 JSON 输出。"
            ),
        },
    ]
    try:
        value = _cached_json(
            cache,
            _key(PROMPT_VERSION + ":verify", question, context, client.config.model),
            client,
            messages,
            max_tokens=600,
        )
    except LLMError:
        return True, "verifier_unavailable"
    supported = value.get("supported")
    if not isinstance(supported, bool):
        return True, "verifier_invalid"
    return supported, str(value.get("reason") or "")


def answer_with_llm(
    question: str,
    hits: list[Any],
    client: LLMClient,
    cache: LLMCache | None = None,
) -> Answer:
    """Compose a cited answer, then enforce citation, number and support checks."""
    if not hits:
        return _abstain("no_evidence")
    hits = _enrich(hits)
    context, by_label = _evidence(hits)
    if not context:
        return _abstain("no_evidence")
    messages = _answer_messages(question, context)
    try:
        value = _cached_json(
            cache,
            _key(PROMPT_VERSION, question, context, client.config.model),
            client,
            messages,
            max_tokens=2400,
        )
    except LLMError as exc:
        if "empty completion" not in str(exc) and "JSON" not in str(exc):
            raise
        retry_messages = [
            *messages,
            {"role": "user", "content": "只输出一个 JSON 对象，不要任何解释或代码块标记。"},
        ]
        value = _cached_json(
            cache,
            _key(PROMPT_VERSION + ":retry", question, context, client.config.model),
            client,
            retry_messages,
            max_tokens=4000,
        )
    if value.get("abstained") is True:
        return _abstain(f"llm_abstain:{str(value.get('reason') or '')}".rstrip(":"))
    text = str(value.get("answer") or "").strip()
    if not text:
        return _abstain("llm_empty")

    problems = _sentence_problems(text, by_label) + _number_problems(text, by_label)
    if problems:
        repaired = _cached_json(
            cache,
            _key(PROMPT_VERSION + ":repair", question, text, client.config.model),
            client,
            _repair_messages(question, context, text, problems),
            max_tokens=2400,
        )
        if repaired.get("abstained") is True:
            return _abstain("llm_repair_abstain")
        text = str(repaired.get("answer") or "").strip()
        if not text:
            return _abstain("llm_repair_empty")
        problems = _sentence_problems(text, by_label) + _number_problems(text, by_label)
        if problems:
            return _abstain("llm_ungrounded:" + problems[0].split(":")[0])

    valid, invalid = _resolve_citations(text, hits)
    if not valid:
        return _abstain("llm_citation_invalid:" + ",".join(invalid[:2]))
    citations = _citations_from_text(text, hits)
    if not citations:
        return _abstain("llm_no_citation")
    supported, reason = _verify(question, text, by_label, client, cache)
    if not supported:
        return _abstain(f"llm_unsupported:{reason}".rstrip(":"))
    return Answer(text=text, citations=citations, abstained=False, reason="llm_compose")


__all__ = ["LLMAnswerError", "PROMPT_VERSION", "answer_with_llm"]
