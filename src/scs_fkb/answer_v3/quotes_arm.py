"""Quote-first exhaustive answering: verbatim facts from every relevant clause."""

from __future__ import annotations

import hashlib
import re
import string
from typing import Any

from ..llm import LLMClient, LLMError, parse_json_object
from ..models import Answer
from ..rag import LLMCache, _citations_from_text
from ..retrieve_v2.rewrite import rewrite
from .llm_answer import _evidence, _verify

PROMPT_VERSION = "quotes-v1"
MAX_HITS = 12
MAX_ENTRIES = 8
MAX_ANSWER_CHARS = 1400

SYSTEM = (
    "你是渔业法规摘录器。给定一个渔民问题和一组证据条款，摘出能够回答问题的原文事实。\n"
    "每条包含：doc_id、section、quote、covers。quote 必须是证据中一段连续原文，不得改写、"
    "不得合并两段、不得补全；covers 用一句话说明它回答问题的哪一部分。\n"
    "只选与问题相关的条款；最多 8 条；证据都不相关就返回空数组。\n"
    '只输出 JSON：{"entries": [{"doc_id": "…", "section": "…", "quote": "…", "covers": "…"}]}'
)

_PUNCT = string.punctuation + "，。；：、（）【】《》“”‘’！？·—…"


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text).strip(string.whitespace)


def _bare(text: str) -> str:
    return "".join(char for char in _squash(text) if char not in _PUNCT).lower()


def _key(question: str, context: str, model: str) -> str:
    digest = hashlib.sha256(
        f"{PROMPT_VERSION}\n{question}\n{context}\n{model}".encode()
    ).hexdigest()
    return f"quotes-{digest[:24]}.json"


def _resolve(entry: dict[str, Any], hits: list[Any]) -> Any:
    doc_id = str(entry.get("doc_id") or "").strip()
    section = str(entry.get("section") or "").strip()
    for hit in hits:
        chunk = hit.chunk
        if chunk.doc_id != doc_id:
            continue
        if section and not (chunk.section.startswith(section) or section in chunk.section):
            continue
        return hit
    return None


def _verbatim(quote: str, text: str) -> bool:
    bare_quote, bare_text = _bare(quote), _bare(text)
    return bool(bare_quote) and bare_quote in bare_text


def _title(hit: Any) -> str:
    chunk = hit.chunk
    return f"{chunk.doc_id} §{chunk.section}" if chunk.section else f"{chunk.doc_id} p.{chunk.page}"


def answer_with_quotes(
    question: str,
    retriever: Any,
    client: LLMClient,
    cache: LLMCache | None = None,
    *,
    fallback: Any = None,
) -> Answer:
    """Extract verbatim quotes per clause, keep the valid ones and merge them."""
    rewrites = rewrite(question, client, cache)
    hits = retriever.search_queries([question, *rewrites], top_k=MAX_HITS)
    if not hits:
        return fallback() if fallback is not None else Answer("", (), True, "no_evidence")
    hits = _enrich(hits)
    context, _by_label = _evidence(hits)
    key = _key(question, context, client.config.model)
    value = cache.get(key) if cache is not None else None
    if value is None:
        messages = [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"问题：\n{question}\n\n证据：\n{context}\n\n按 JSON 输出。",
            },
        ]
        try:
            value = parse_json_object(client.chat(messages, max_tokens=1800))
        except LLMError:
            return fallback() if fallback is not None else Answer("", (), True, "model_error")
        if cache is not None:
            cache.put(key, value)

    entries: list[tuple[str, str, Any]] = []
    rejected = 0
    for entry in value.get("entries") or []:
        quote = str((entry or {}).get("quote") or "").strip()
        hit = _resolve(entry or {}, hits)
        if not quote or hit is None or not _verbatim(quote, hit.chunk.text):
            rejected += 1
            continue
        entries.append((quote, _title(hit), hit))
        if len(entries) >= MAX_ENTRIES:
            break
    if not entries:
        if fallback is not None:
            return fallback()
        return Answer("", (), True, "no_verbatim_entries")

    lines = [f"结论：{entries[0][0]} [{entries[0][1]}]"]
    for index, (quote, label, _hit) in enumerate(entries, start=1):
        lines.append(f"{index}. {quote} [{label}]")
    text = "\n".join(lines)
    if len(text) > MAX_ANSWER_CHARS:
        text = text[:MAX_ANSWER_CHARS].rsplit("\n", 1)[0]

    citations = _citations_from_text(text, hits)
    if not citations:
        return fallback() if fallback is not None else Answer("", (), True, "no_citation")
    supported, reason = _verify(question, text, _by_label, client, cache)
    if not supported:
        return fallback() if fallback is not None else Answer("", (), True, f"unsupported:{reason}")
    return Answer(text=text, citations=citations, abstained=False, reason="quotes_compose")


def _enrich(hits: list[Any]) -> list[Any]:
    from .llm_answer import _enrich as enrich

    return enrich(hits)


__all__ = ["MAX_ENTRIES", "answer_with_quotes", "PROMPT_VERSION"]
