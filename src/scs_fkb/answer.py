from __future__ import annotations

import re

from .models import Answer, Citation, SearchHit
from .text import tokenize

CITATION_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_-]*)(?: p\.(\d+))?(?: §([^\]]+))?\]")
SENTENCE_RE = re.compile(r"(?<=[。！？；])\s*|\n+")
DATE_RANGE_RE = re.compile(r"\d{1,2}月\d{1,2}日.*?至.*?\d{1,2}月\d{1,2}日")
TIME_WORDS = ("时间", "日期", "起止", "何时", "几月", "几号", "期间")
IMPLEMENTATION_WORDS = ("实施", "生效", "施行")


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_RE.split(text) if part.strip()]


def _is_heading(sentence: str) -> bool:
    if re.search(r"[。！？；]", sentence):
        return False
    if len(sentence) > 60:
        return False
    article = re.match(r"^第[一二三四五六七八九十百零〇]+条$", sentence)
    section = re.match(r"^[一二三四五六七八九十]+、[^\n]{1,40}$", sentence)
    return bool(article or section)


def _best_sentence(question: str, text: str) -> str | None:
    query_tokens = set(tokenize(question))
    if not query_tokens:
        return None
    candidates = _sentences(text)
    if any(word in question for word in TIME_WORDS) and not any(
        word in question for word in IMPLEMENTATION_WORDS
    ):
        dated = [sentence for sentence in candidates if DATE_RANGE_RE.search(sentence)]
        if dated:
            candidates = dated
    if "证书" in question:
        certificate_sentences = [sentence for sentence in candidates if "证书" in sentence]
        if certificate_sentences:
            candidates = certificate_sentences
    best: str | None = None
    best_score = 0.0
    for sentence in candidates:
        if len(sentence) < 6 or _is_heading(sentence):
            continue
        score = len(query_tokens & set(tokenize(sentence)))
        if score <= 0:
            continue
        score += min(len(sentence), 120) / 1000.0
        if score > best_score:
            best = sentence
            best_score = score
    return best


def _with_context(hit: SearchHit, sentence: str) -> str:
    if not sentence.startswith("（"):
        return sentence
    sentences = _sentences(hit.chunk.text)
    if not sentences:
        return sentence
    first = sentences[0]
    if first == sentence or _is_heading(first) or len(first) > 300:
        return sentence
    return f"{first}\n{sentence}"


def make_citation(hit: SearchHit, snippet: str) -> Citation:
    return Citation(
        doc_id=hit.chunk.doc_id,
        title=hit.chunk.doc_id,
        page=hit.chunk.page,
        section=hit.chunk.section,
        snippet=snippet,
        score=hit.score,
    )


def citation_text(citation: Citation) -> str:
    parts = [citation.doc_id]
    if citation.page:
        parts.append(f"p.{citation.page}")
    if citation.section:
        parts.append(f"§{citation.section}")
    return "[" + " ".join(parts) + "]"


def _citation_key(doc_id: str, page: str | None, section: str | None) -> tuple[str, int, str]:
    return (doc_id, int(page) if page else 0, section or "")


def validate_citations(text: str, hits: list[SearchHit]) -> tuple[bool, list[str]]:
    allowed = {(hit.chunk.doc_id, hit.chunk.page, hit.chunk.section) for hit in hits}
    citations = CITATION_RE.findall(text)
    if not citations:
        return False, ["no citation"]
    invalid: list[str] = []
    for doc_id, page, section in citations:
        key = _citation_key(doc_id, page, section)
        if key not in allowed:
            invalid.append(f"{doc_id} p.{key[1]} §{key[2]}")
    return not invalid, invalid


def _matched_tokens(question: str, hit: SearchHit) -> int:
    query_tokens = set(tokenize(question))
    if not query_tokens:
        return 0
    return len(query_tokens & set(tokenize(hit.chunk.text)))


def answer_question(
    question: str,
    hits: list[SearchHit],
    max_evidence: int = 3,
    min_score: float = 0.0,
    min_matched: int = 3,
) -> Answer:
    """Answer from retrieved hits, abstaining when the best evidence is weak.

    The gate is deliberately simple and measurable: the top chunk must reach
    ``min_score`` and share at least ``min_matched`` distinct query tokens. The
    thresholds are calibrated on the draft question set, not learned.
    """
    usable = [hit for hit in hits if hit.score > 0]
    if not usable:
        return Answer(
            text="证据不足：索引语料中没有找到可支持回答的内容。",
            abstained=True,
            reason="no_evidence",
        )

    best = usable[0]
    required = min(min_matched, len(set(tokenize(question))))
    matched = _matched_tokens(question, best)
    if best.score < min_score or matched < required:
        return Answer(
            text="证据不足：检索到的证据覆盖不足，无法支持回答。",
            abstained=True,
            reason="weak_evidence",
        )

    lines: list[str] = []
    citations: list[Citation] = []
    seen: set[tuple[str, str, str]] = set()
    for hit in usable[:max_evidence]:
        sentence = _best_sentence(question, hit.chunk.text)
        if not sentence:
            continue
        sentence = _with_context(hit, sentence)
        key = (hit.chunk.doc_id, hit.chunk.section, sentence)
        if key in seen:
            continue
        seen.add(key)
        citation = make_citation(hit, sentence)
        citations.append(citation)
        lines.append(f"{sentence} {citation_text(citation)}")

    if not lines:
        return Answer(
            text="证据不足：检索到的片段没有覆盖问题中的关键内容。",
            abstained=True,
            reason="no_evidence",
        )

    text = "\n".join(lines)
    ok, invalid = validate_citations(text, usable)
    if not ok:
        return Answer(
            text=f"引用校验失败：{'; '.join(invalid)}",
            abstained=True,
            reason="citation_invalid",
        )
    return Answer(text=text, citations=citations, abstained=False, reason="ok")
