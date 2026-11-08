"""Evidence-sufficiency judge for answers outside the LLM composition arm.

The judge decides whether the retrieved clauses contain the fact the question
asks for (a value, deadline, procedure, responsible body or penalty), so that a
weak match abstains instead of answering with a related clause.
"""

from __future__ import annotations

import hashlib
from typing import Any

from ..llm import LLMClient, LLMError, parse_json_object
from ..rag import LLMCache

PROMPT_VERSION = "sufficiency-v1"
MAX_HITS = 6
MAX_CHARS = 5000

SYSTEM = (
    "你是证据充分性判定器。给定渔民问题和检索到的条款，判断这些条款是否直接包含问题所问的"
    "具体事实：数值、期限、比例、办理层级、材料、责任主体或处罚幅度。\n"
    "只与主题相关、只覆盖部分子问题都算 partial；完全没有相关条款算 none。\n"
    '只输出 JSON：{"sufficiency": "full|partial|none", "reason": "简短理由"}'
)


def _key(question: str, context: str, model: str) -> str:
    digest = hashlib.sha256(f"{PROMPT_VERSION}\n{question}\n{context}\n{model}".encode())
    return f"suff-{digest.hexdigest()[:24]}.json"


def _context(hits: list[Any]) -> str:
    parts: list[str] = []
    used = 0
    for hit in hits[:MAX_HITS]:
        chunk = hit.chunk
        section = f" §{chunk.section}" if chunk.section else f" p.{chunk.page}"
        block = f"[{chunk.doc_id}{section}] {' '.join(chunk.text.split())[:800]}"
        if used + len(block) > MAX_CHARS:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


def judge(
    question: str,
    hits: list[Any],
    client: LLMClient | None,
    cache: LLMCache | None,
) -> str:
    """Return full, partial or none; default to full when the judge is unavailable."""
    if client is None or not hits:
        return "full"
    context = _context(hits)
    key = _key(question, context, client.config.model)
    value = cache.get(key) if cache is not None else None
    if value is None:
        messages = [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"问题：\n{question}\n\n条款：\n{context}\n\n按 JSON 输出。",
            },
        ]
        try:
            value = parse_json_object(client.chat(messages, max_tokens=500))
        except LLMError:
            return "full"
        if cache is not None:
            cache.put(key, value)
    verdict = str(value.get("sufficiency") or "full").lower()
    return verdict if verdict in ("full", "partial", "none") else "full"


__all__ = ["PROMPT_VERSION", "judge"]
