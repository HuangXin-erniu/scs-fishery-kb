"""Query rewriting for retrieval: colloquial fisher questions to normative queries."""

from __future__ import annotations

import hashlib

from ..llm import LLMClient, LLMError, parse_json_object
from ..rag import LLMCache

PROMPT_VERSION = "query-rewrite-v1"
MAX_QUERIES = 3

SYSTEM = (
    "你是渔业法规检索助手。把渔民的口语问题改写成 2–3 条用于检索法规、标准或统计口径的"
    "规范中文查询：保留数字、地名、船型与物种名，补全口语省略（如“上排”=渔船维修离港、"
    "“送冰”=渔获物运输辅助船、“扣船”=扣押渔船），不要回答问题。\n"
    '只输出 JSON：{"queries": ["……", "……"]}'
)


def _key(question: str, model: str) -> str:
    digest = hashlib.sha256(f"{PROMPT_VERSION}\n{question}\n{model}".encode()).hexdigest()
    return f"rewrite-{digest[:24]}.json"


def rewrite(
    question: str,
    client: LLMClient | None,
    cache: LLMCache | None,
    *,
    lexicon_groups: list[dict[str, object]] | None = None,
) -> list[str]:
    """Return two or three normative queries; fall back to lexicon expansion."""
    if client is not None:
        key = _key(question, client.config.model)
        cached = cache.get(key) if cache is not None else None
        if cached is None:
            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"问题：{question}\n\n按 JSON 输出。"},
            ]
            try:
                cached = parse_json_object(client.chat(messages, max_tokens=600))
            except LLMError:
                cached = None
            if cached is not None and cache is not None:
                cache.put(key, cached)
        if isinstance(cached, dict):
            queries = [
                str(item).strip() for item in (cached.get("queries") or []) if str(item).strip()
            ][:MAX_QUERIES]
            if queries:
                return queries
    from ..lexicon import expand_query

    expanded = expand_query(question, lexicon_groups)
    return [expanded] if expanded != question else []


__all__ = ["PROMPT_VERSION", "rewrite"]
