"""Decompose a question into independently answerable facets."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..llm import LLMClient, LLMError, parse_json_object
from ..rag import LLMCache

PROMPT_VERSION = "facet-decompose-v1"
MAX_FACETS = 5
TYPES = {"core", "background", "follow-up"}

SYSTEM = (
    "你是渔业问答拆解器。把渔民的问题拆成 2–5 个可以各自用一条法规/标准条款回答的子问题。\n"
    "规则：每个子问题必须是单一事实（一个数值、一个期限、一个条件、一个办理层级或一个渠道）；"
    "保留原问题里的数字、地名、船型、物种；第一个子问题标 core，其余标 background 或 follow-up；"
    "不要把问题本身复制成子问题，不要回答问题。\n"
    '只输出 JSON：{"facets": [{"text": "……", "type": "core"}]}'
)


@dataclass(frozen=True)
class Facet:
    text: str
    kind: str = "core"


def _key(question: str, model: str) -> str:
    digest = hashlib.sha256(f"{PROMPT_VERSION}\n{question}\n{model}".encode()).hexdigest()
    return f"facet-{digest[:24]}.json"


def decompose(
    question: str,
    client: LLMClient | None,
    cache: LLMCache | None,
    *,
    max_facets: int = MAX_FACETS,
) -> list[Facet]:
    """Return the facets, or the question itself when the model is unavailable."""
    fallback = [Facet(text=question, kind="core")]
    if client is None:
        return fallback
    key = _key(question, client.config.model)
    value = cache.get(key) if cache is not None else None
    if value is None:
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"问题：{question}\n\n按 JSON 输出。"},
        ]
        try:
            value = parse_json_object(client.chat(messages, max_tokens=700))
        except LLMError:
            return fallback
        if cache is not None and isinstance(value, dict):
            cache.put(key, value)
    if not isinstance(value, dict):
        return fallback
    facets: list[Facet] = []
    for item in value.get("facets") or []:
        text = str((item or {}).get("text") or "").strip()
        if not text or len(text) < 4:
            continue
        kind = str((item or {}).get("type") or "background").strip().lower()
        facets.append(Facet(text=text, kind=kind if kind in TYPES else "background"))
    if not facets:
        return fallback
    return facets[:max_facets]


__all__ = ["Facet", "decompose", "MAX_FACETS", "PROMPT_VERSION"]
