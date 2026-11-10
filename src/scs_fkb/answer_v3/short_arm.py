"""Short worker answer: conclusion, cited basis and an optional deadline.

The arm is optional. It renders at most 300 Chinese characters, enforces the
same citation and number checks as the long arm and raises on failure so the
caller can fall back to the deterministic path.
"""

from __future__ import annotations

import hashlib
from typing import Any

from ..llm import LLMClient, LLMError
from ..models import Answer
from ..rag import LLMCache, _citations_from_text
from .llm_answer import (
    _cached_json,
    _enrich,
    _evidence,
    _key,
    _number_problems,
    _resolve_citations,
    _sentence_problems,
)

PROMPT_VERSION = "short-v1"
MAX_ANSWER_CHARS = 300
MAX_HITS = 8
MAX_BASIS = 4

SYSTEM = (
    "你是南海近海渔业知识库的短答器，只能使用给出的证据，禁止外部知识。\n"
    "输出 JSON："
    '{"conclusion": "……", "basis": ["……"], "deadline": "……", '
    '"documents": ["……"], "caveat": "……"}\n'
    "要求：\n"
    "1. conclusion 第一句直接回答（数值、是否、时限或办理路径），并带 [DOC_ID §章节] 引用，"
    "例如：[POL-CLOS-015 §三、休渔时间]。\n"
    "2. basis 给 1-4 条依据，每条一句，必须有引用，数字逐字来自证据。\n"
    "3. deadline 写时间节点，documents 写要带的材料，没有就给空字符串或空数组；"
    "只要写了事实性内容，同样要带引用。\n"
    "4. 全文不超过 280 个汉字；不要复述法条，不要写“根据……规定”之类的空话。\n"
    "5. 证据不足时不要编：conclusion 写“证据不足：……”并说明缺什么。\n"
    "只输出 JSON，不要代码块。"
)

REPAIR = (
    "下面这份短答没有通过校验。请在不引入新事实的前提下修复：删除无依据数字、"
    "给缺引用的句子补正确引用、把总长度压到 280 字以内。保持同样的 JSON 字段。\n"
    '只输出 JSON：{"conclusion": "……", "basis": ["……"], "deadline": "……", '
    '"documents": ["……"], "caveat": "……"}'
)


def _key_for(question: str, context: str, model: str) -> str:
    digest = hashlib.sha256(
        f"{PROMPT_VERSION}\n{question}\n{context}\n{model}".encode()
    ).hexdigest()
    return f"short-{digest[:24]}.json"


def _render(value: dict[str, Any]) -> str:
    conclusion = str(value.get("conclusion") or "").strip()
    lines = [conclusion] if conclusion else []
    basis = [str(item).strip() for item in value.get("basis") or [] if str(item).strip()]
    if basis:
        lines.append("依据：" + "；".join(basis[:MAX_BASIS]))
    deadline = str(value.get("deadline") or "").strip()
    if deadline:
        lines.append("期限：" + deadline)
    documents = [str(item).strip() for item in value.get("documents") or [] if str(item).strip()]
    if documents:
        lines.append("材料：" + "、".join(documents))
    caveat = str(value.get("caveat") or "").strip()
    if caveat:
        lines.append("提醒：" + caveat)
    return "\n".join(line for line in lines if line)


def _ask(
    cache: LLMCache | None,
    key: str,
    client: LLMClient,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 1600,
) -> dict[str, Any]:
    try:
        return _cached_json(cache, key, client, messages, max_tokens=max_tokens)
    except LLMError as exc:
        if "empty completion" not in str(exc) and "JSON" not in str(exc):
            raise
        retry = [
            *messages,
            {"role": "user", "content": "只输出一个 JSON 对象，不要解释或代码块标记。"},
        ]
        return _cached_json(cache, key + ":retry", client, retry, max_tokens=3000)


def _problems(text: str, by_label: dict[str, Any]) -> list[str]:
    # A material list is a noun phrase, not a claim; every other line needs a citation.
    claims = "\n".join(line for line in text.splitlines() if not line.startswith("材料："))
    return _sentence_problems(claims, by_label) + _number_problems(text, by_label)


def answer_with_short(
    question: str,
    hits: list[Any],
    client: LLMClient,
    cache: LLMCache | None = None,
) -> Answer:
    if not hits:
        raise LLMError("short_no_evidence")
    hits = _enrich(hits)
    context, by_label = _evidence(hits)
    if not context:
        raise LLMError("short_no_context")
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": f"问题：\n{question}\n\n证据清单：\n{context}\n\n按 JSON 输出。",
        },
    ]
    value = _ask(
        cache,
        _key_for(question, context, client.config.model),
        client,
        messages,
    )
    text = _render(value)
    if not text:
        raise LLMError("short_empty")
    problems = _problems(text, by_label) + (
        [f"too_long:{len(text)}"] if len(text) > MAX_ANSWER_CHARS else []
    )
    if problems:
        repaired = _ask(
            cache,
            _key(PROMPT_VERSION + ":repair", question, text, client.config.model),
            client,
            [
                {"role": "system", "content": REPAIR},
                {
                    "role": "user",
                    "content": (
                        f"问题：\n{question}\n\n证据清单：\n{context}\n\n"
                        f"待修复短答：\n{text}\n\n问题：{'；'.join(problems[:5])}\n\n按 JSON 输出。"
                    ),
                },
            ],
            max_tokens=2200,
        )
        text = _render(repaired)
        problems = _problems(text, by_label) + (
            [f"too_long:{len(text)}"] if len(text) > MAX_ANSWER_CHARS else []
        )
        if problems:
            raise LLMError("short_invalid:" + problems[0].split(":")[0])
    valid, invalid = _resolve_citations(text, hits)
    if not valid:
        raise LLMError("short_citation_invalid:" + ",".join(invalid[:2]))
    citations = _citations_from_text(text, hits)
    if not citations:
        raise LLMError("short_no_citation")
    return Answer(text=text, citations=citations, abstained=False, reason="short_compose")


__all__ = ["MAX_ANSWER_CHARS", "PROMPT_VERSION", "answer_with_short"]
