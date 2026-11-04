from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .answer import CITATION_RE, answer_question, make_citation, validate_citations
from .llm import PROMPT_VERSION, LLMClient, LLMError
from .models import Answer

JUDGE_PROMPT_VERSION = f"{PROMPT_VERSION}-judge"
ANSWER_PROMPT_VERSION = f"{PROMPT_VERSION}-answer"
SCORE_PROMPT_VERSION = f"{PROMPT_VERSION}-score"


def public_hits(hits: list[Any]) -> list[Any]:
    """Keep only public chunks; internal and restricted text never leaves the machine."""
    return [hit for hit in hits if getattr(hit.chunk, "sensitivity", "public") == "public"]


def evidence_block(hits: list[Any], max_chars: int = 6000) -> str:
    parts: list[str] = []
    used = 0
    for index, hit in enumerate(hits, start=1):
        chunk = hit.chunk
        section = f" §{chunk.section}" if chunk.section else ""
        page = f" p.{chunk.page}" if chunk.page else ""
        header = f"[{index}] {chunk.doc_id}{section}{page}"
        text = " ".join(chunk.text.split())
        block = f"{header}\n{text}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


def _key(kind: str, question: str, context: str, model: str) -> str:
    digest = hashlib.sha256(f"{kind}\n{question}\n{context}\n{model}".encode()).hexdigest()
    return f"{kind}-{digest[:24]}.json"


class LLMCache:
    """Response cache keyed by prompt version, question, evidence and model."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> dict | None:
        path = self.root / key
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def put(self, key: str, value: dict) -> None:
        try:
            (self.root / key).write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass


def _cached_call(
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
    raw = client.chat_json(messages, max_tokens=max_tokens)
    if cache is not None:
        cache.put(key, raw)
    return raw


def judge_evidence(
    question: str,
    hits: list[Any],
    client: LLMClient,
    cache: LLMCache | None = None,
) -> dict:
    context = evidence_block(hits)
    key = _key(JUDGE_PROMPT_VERSION, question, context, client.config.model)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict evidence judge for a fishery knowledge base. "
                "Use only the supplied evidence; no outside knowledge. "
                "Answerable is true when the evidence contains at least one concrete fact "
                "that directly answers the question; a partial but substantive answer counts. "
                "Topical discussion, general rules that do not address the asked fact, or "
                "examples about other places do not count. If the question asks about a "
                "specific but unnamed place or record (for example '某渔场') and the evidence "
                "only gives examples for other named places, answerable is false. If the "
                "question asks for a specific historical record, season or species and the "
                "evidence only gives general background, answerable is false. "
                'Return JSON only: {"answerable": true or false, "reason": "short reason"}.'
            ),
        },
        {
            "role": "user",
            "content": f"Question:\n{question}\n\nEvidence:\n{context}",
        },
    ]
    value = _cached_call(cache, key, client, messages, max_tokens=1600)
    answerable = value.get("answerable")
    if not isinstance(answerable, bool):
        raise LLMError("judge reply has no boolean answerable field")
    return {"answerable": answerable, "reason": str(value.get("reason") or "")}


def _clean_citations(text: str) -> str:
    """Drop a dangling section marker such as ``[DOC p.2 §]``."""
    return re.sub(r"\s*§\s*\]", "]", text)


def _citations_from_text(text: str, hits: list[Any]) -> list[Any]:
    citations = []
    seen: set[tuple[str, int, str]] = set()
    for doc_id, page, section in CITATION_RE.findall(text):
        for hit in hits:
            chunk = hit.chunk
            if chunk.doc_id != doc_id:
                continue
            if page and chunk.page != int(page):
                continue
            if section and not chunk.section.startswith(section):
                continue
            key = (chunk.doc_id, chunk.page, chunk.section)
            if key in seen:
                continue
            seen.add(key)
            citations.append(make_citation(hit, " ".join(chunk.text.split())[:160]))
            break
    return citations


def generate_answer(
    question: str,
    hits: list[Any],
    client: LLMClient,
    cache: LLMCache | None = None,
) -> Answer:
    context = evidence_block(hits)
    key = _key(ANSWER_PROMPT_VERSION, question, context, client.config.model)
    messages = [
        {
            "role": "system",
            "content": (
                "You answer questions about South China Sea nearshore fisheries using only "
                "the supplied evidence. Every factual sentence must end with a citation in "
                "the form [DOC_ID §section] or [DOC_ID p.PAGE], using the exact identifiers "
                "from the evidence. Do not use outside knowledge. If the evidence does not "
                "contain the answer, abstain. Return JSON only: "
                '{"abstained": true or false, "answer": "text", "reason": "short reason"}.'
            ),
        },
        {
            "role": "user",
            "content": f"Question (answer every part):\n{question}\n\nEvidence:\n{context}",
        },
    ]
    value = _cached_call(cache, key, client, messages, max_tokens=4000)
    abstained = value.get("abstained")
    if not isinstance(abstained, bool):
        raise LLMError("answer reply has no boolean abstained field")
    text = _clean_citations(str(value.get("answer") or "").strip())
    reason = str(value.get("reason") or "")
    if abstained or not text:
        return Answer(
            text="证据不足：检索到的证据不足以支持回答。",
            abstained=True,
            reason=f"llm_abstain:{reason}" if reason else "llm_abstain",
        )
    valid, invalid = validate_citations(text, hits)
    if not valid:
        return Answer(
            text="证据不足：生成的引用无法在检索证据中解析。",
            abstained=True,
            reason=f"llm_citation_invalid:{','.join(invalid[:2])}",
        )
    citations = _citations_from_text(text, hits)
    if not citations:
        return Answer(
            text="证据不足：生成的回答没有引用。",
            abstained=True,
            reason="llm_no_citation",
        )
    return Answer(text=text, citations=citations, abstained=False, reason="llm")


def score_answer(
    question: str,
    gold_points: list[str],
    answer_text: str,
    evidence: str,
    client: LLMClient,
    cache: LLMCache | None = None,
) -> dict:
    key = _key(
        SCORE_PROMPT_VERSION,
        question,
        "\n".join(gold_points) + "\n" + answer_text + "\n" + evidence,
        client.config.model,
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict evaluator. Compare the candidate answer with the gold "
                "answer points and the evidence. Score correctness (0-1), completeness "
                "(0-1) and faithfulness (0-1). A score of 1 means fully correct, fully "
                "covering the gold points, or fully supported by the evidence. Do not reward "
                "length. Return JSON only: "
                '{"correctness": 0.0, "completeness": 0.0, "faithfulness": 0.0, '
                '"reason": "short reason"}.'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\nGold answer points:\n"
                + "\n".join(f"- {point}" for point in gold_points)
                + f"\n\nCandidate answer:\n{answer_text}\n\nEvidence:\n{evidence}"
            ),
        },
    ]
    value = _cached_call(cache, key, client, messages, max_tokens=1600)
    scores = {}
    for name in ("correctness", "completeness", "faithfulness"):
        raw = value.get(name)
        try:
            score = float(raw)
        except (TypeError, ValueError) as exc:
            raise LLMError(f"score reply has no numeric {name}") from exc
        scores[name] = round(min(1.0, max(0.0, score)), 4)
    scores["reason"] = str(value.get("reason") or "")
    return scores


def llm_answer_fn(client: LLMClient, cache: LLMCache | None = None):
    """Build the answer callable used by ask/eval with --llm."""

    def answer(question: str, hits: list[Any]) -> Answer:
        usable = public_hits(hits)
        if not usable:
            return Answer(
                text="证据不足：没有可用的公开证据。",
                abstained=True,
                reason="no_public_evidence",
            )
        try:
            judged = judge_evidence(question, usable, client, cache)
            if not judged["answerable"]:
                return Answer(
                    text="证据不足：检索到的证据不足以支持回答。",
                    abstained=True,
                    reason=f"llm_judge:{judged['reason']}",
                )
            generated = generate_answer(question, usable, client, cache)
            if generated.abstained and generated.reason.startswith(
                ("llm_citation_invalid", "llm_no_citation", "llm_abstain")
            ):
                return answer_question(
                    question,
                    usable,
                    min_score=0.0,
                    min_matched=0,
                )
            return generated
        except LLMError:
            return answer_question(
                question,
                usable,
                min_score=0.0,
                min_matched=0,
            )

    return answer


__all__ = [
    "ANSWER_PROMPT_VERSION",
    "JUDGE_PROMPT_VERSION",
    "LLMCache",
    "SCORE_PROMPT_VERSION",
    "evidence_block",
    "generate_answer",
    "judge_evidence",
    "llm_answer_fn",
    "public_hits",
    "score_answer",
]
