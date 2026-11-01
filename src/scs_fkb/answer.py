from __future__ import annotations

import re

from .models import Answer, Citation, SearchHit
from .text import tokenize

CITATION_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_-]*)(?: p\.(\d+))?(?: §([^\]]+))?\]")
SENTENCE_RE = re.compile(r"(?<=[。！？；])\s*|\n+")
DATE_RANGE_RE = re.compile(r"\d{1,2}月\d{1,2}日.*?至.*?\d{1,2}月\d{1,2}日")
TIME_WORDS = ("时间", "日期", "起止", "何时", "几月", "几号", "期间")
IMPLEMENTATION_WORDS = ("实施", "生效", "施行")
OUT_OF_SCOPE_TERMS = (
    "产量",
    "统计",
    "年鉴",
    "渔汛",
    "叶绿素",
    "海表温度",
    "sst",
    "航次",
    "渔具标准",
    "网目",
    "渔情",
    "中心渔场",
    "cpue",
)


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
        candidates = [sentence for sentence in candidates if DATE_RANGE_RE.search(sentence)]
        if not candidates:
            return None
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


def answer_question(question: str, hits: list[SearchHit], max_evidence: int = 3) -> Answer:
    normalized = question.lower()
    if any(term in normalized for term in OUT_OF_SCOPE_TERMS):
        return Answer(
            text="证据不足：当前法律子集不包含统计、渔情、渔具或航次类来源。",
            abstained=True,
            reason="out_of_scope",
        )
    usable = [hit for hit in hits if hit.score > 0]
    if not usable:
        return Answer(
            text="证据不足：索引语料中没有找到可支持回答的内容。",
            abstained=True,
            reason="no_evidence",
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
