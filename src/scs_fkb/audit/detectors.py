from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from scs_fkb.audit.normalize import (
    CITATION_RE,
    citations,
    entities,
    jaccard,
    ngrams,
    numbers,
    sentences,
)
from scs_fkb.audit.schema import AuditRecord, Finding

D1_MARKERS = ("原文：", "×10", "网站地图", "第X卷第X期", "打印本页")
D4_MARKERS = ("完整性校验未通过", "作答器不可用", "结论没有可解析的引用")
QUESTION_STOP = {"什么", "多少", "怎么", "可以", "是否", "以及", "超过", "有没有", "要不要"}


def _texts_for(
    record: AuditRecord, chunk_index: dict[str, list[tuple[str, str]]]
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for doc_id in record.evidence_ids:
        for section, text in chunk_index.get(doc_id, []):
            out.append((section, text))
    return out


def _containment(sentence: str, chunk: str) -> float:
    grams = ngrams(sentence)
    if not grams:
        return 0.0
    return len(grams & ngrams(chunk)) / len(grams)


def _unigram_containment(sentence: str, chunk: str) -> float:
    clean = re.sub(r"[^\u4e00-\u9fff0-9A-Za-z]", "", CITATION_RE.sub("", sentence))
    if not clean:
        return 0.0
    chunk_chars = set(re.sub(r"[^\u4e00-\u9fff0-9A-Za-z]", "", chunk))
    return sum(1 for char in set(clean) if char in chunk_chars) / len(set(clean))


def _cited_texts(
    record: AuditRecord, chunk_index: dict[str, list[tuple[str, str]]]
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for cite in record.citations:
        doc_id = str(cite.get("doc_id", ""))
        section = str(cite.get("section", ""))
        for sec, text in chunk_index.get(doc_id, []):
            if not section or sec.startswith(section) or section.startswith(sec):
                out.append((section or sec, text))
    return out


def d1(record: AuditRecord, chunks: list[tuple[str, str]]) -> list[Finding]:
    text = record.visible_answer or ""
    findings: list[Finding] = []
    for marker in D1_MARKERS:
        if marker in text:
            findings.append(Finding(record.id, "D1", "S2", marker, chunk_id=""))
    best = 0.0
    best_sec = ""
    for section, chunk in chunks:
        if not chunk or not text:
            continue
        block = SequenceMatcher(None, text, chunk, autojunk=False).find_longest_match(
            0, len(text), 0, len(chunk)
        )
        ratio = block.size / max(1, len(text))
        if ratio > best:
            best, best_sec = ratio, section
    if best > 0.80:
        findings.append(Finding(record.id, "D1", "S2", f"字符包含率={best:.2f}", chunk_id=best_sec))
    return findings


def d2(record: AuditRecord) -> list[Finding]:
    match = re.search(r"口径[:：]\s*(.+)", record.visible_answer or "", re.S)
    if not match:
        return []
    scope = match.group(1)
    q_entities, a_entities = entities(record.question), entities(scope)
    if a_entities and not (q_entities & a_entities):
        return [Finding(record.id, "D2", "S2", scope[:160], chunk_id="")]
    return []


def d3(record: AuditRecord) -> list[Finding]:
    text = (record.visible_answer or "").rstrip()
    if not text:
        return []
    findings: list[Finding] = []
    if text.count("[") != text.count("]"):
        findings.append(Finding(record.id, "D3", "S2", "方括号不配平", chunk_id=""))
    if text.count("（") != text.count("）"):
        findings.append(Finding(record.id, "D3", "S2", "圆括号不配平", chunk_id=""))
    if text[-1] not in "。！？；）】]":
        findings.append(Finding(record.id, "D3", "S2", f"结尾={text[-1]!r}", chunk_id=""))
    return findings


def d4(record: AuditRecord) -> list[Finding]:
    return [
        Finding(record.id, "D4", "S2", marker, chunk_id="")
        for marker in D4_MARKERS
        if marker in (record.visible_answer or "")
    ]


def d5(record: AuditRecord, chunks: list[tuple[str, str]]) -> list[Finding]:
    if not record.abstained:
        return []
    grams = {part for part in ngrams(record.question, 2) if part not in QUESTION_STOP}
    if not grams:
        return []
    evidence = "\n".join(text for _section, text in chunks)
    coverage = sum(1 for gram in grams if gram in evidence) / len(grams)
    if coverage >= 0.60:
        return [Finding(record.id, "D5", "S1", f"证据覆盖={coverage:.2f}", chunk_id="")]
    return []


def d6(record: AuditRecord) -> list[Finding]:
    if record.abstained:
        return []
    parts = [part.strip() for part in re.split(r"[？?；;]", record.question or "") if part.strip()]
    if len(parts) < 2:
        return []
    wanted = set()
    for part in parts:
        wanted |= entities(part)
    if not wanted:
        return []
    answer_entities = entities(record.visible_answer or "")
    coverage = len(wanted & answer_entities) / len(wanted)
    if coverage < 0.50:
        return [Finding(record.id, "D6", "S2", f"子问实体覆盖={coverage:.2f}", chunk_id="")]
    return []


def d7(record: AuditRecord, chunk_index: dict[str, list[tuple[str, str]]]) -> list[Finding]:
    findings: list[Finding] = []
    for sentence in sentences(record.visible_answer or ""):
        if any(
            marker in sentence
            for marker in ("证据未", "未覆盖", "未规定", "无法", "不能据此", "缺口", "未收录")
        ):
            continue
        claim = re.sub(r"[。；，, \[\]（）()\s]", "", CITATION_RE.sub("", sentence))
        if len(claim) < 12:
            continue
        cites = citations(sentence)
        if not cites:
            continue
        supported = False
        first_bad: tuple[str, str] | None = None
        for doc_id, section in cites:
            candidates = chunk_index.get(doc_id, [])
            matched = [
                (sec, text)
                for sec, text in candidates
                if not section or sec.startswith(section) or section.startswith(sec)
            ]
            if not matched:
                first_bad = first_bad or (doc_id, section)
                continue
            if any(
                max(
                    jaccard(claim, text),
                    _containment(claim, text),
                    _unigram_containment(claim, text) * 0.9 if len(claim) <= 40 else 0.0,
                )
                >= 0.25
                for _sec, text in matched
            ):
                supported = True
                break
            first_bad = first_bad or (doc_id, section)
        if not supported and first_bad:
            doc_id, section = first_bad
            findings.append(
                Finding(record.id, "D7", "S1", sentence[:160], f"{doc_id} §{section}", doc_id)
            )
    return findings


def d8(record: AuditRecord, doc_meta: dict[str, dict[str, Any]]) -> list[Finding]:
    """A national-scope assertion must cite a national document.

    The check is sentence-scoped: a gap line such as "全国层面统一规定未覆盖"
    is not an assertion and must not flag every provincial citation in the
    answer.
    """
    findings: list[Finding] = []
    for sentence in sentences(record.visible_answer or ""):
        if any(
            marker in sentence
            for marker in ("缺口", "未覆盖", "未收录", "未明确", "注意：", "渠道：", "时效：")
        ):
            continue
        national_claim = "全国" in sentence or "适用于全国" in sentence
        current_claim = "现行" in sentence
        if not national_claim and not current_claim:
            continue
        for doc_id, _section in citations(sentence):
            meta = doc_meta.get(doc_id, {})
            level = str(meta.get("level", ""))
            if national_claim and level and level not in {"national", "国家"}:
                findings.append(
                    Finding(
                        record.id,
                        "D8",
                        "S1",
                        "全国性断言引用非国家级文档",
                        doc_id,
                        doc_id,
                    )
                )
            effective_to = str(meta.get("effective_to", "") or "")
            if current_claim and effective_to and effective_to < "2026-01-01":
                findings.append(
                    Finding(
                        record.id,
                        "D8",
                        "S1",
                        "过期文档仍称现行",
                        doc_id,
                        doc_id,
                    )
                )
    return findings


def d9(record: AuditRecord, cited_chunks: list[tuple[str, str]]) -> list[Finding]:
    cited = "\n".join(text for _section, text in cited_chunks)
    lines = [
        line
        for line in (record.visible_answer or "").splitlines()
        if not line.strip().startswith(("时效：", "口径：", "注意：", "缺口", "渠道：", "版本："))
    ]
    clean = re.sub(r"\[[^\]]+\]", "", "\n".join(lines))
    missing = [value for value in numbers(clean) if value not in cited]
    if missing:
        return [Finding(record.id, "D9", "S1", f"未落地数值={missing[:5]}", chunk_id="")]
    return []


def d10(record: AuditRecord) -> list[Finding]:
    q_provinces = {
        name
        for name in ("广西", "广东", "福建", "海南", "浙江", "山东", "江苏", "辽宁", "河北")
        if name in record.question
    }
    a_provinces = {
        name
        for name in ("广西", "广东", "福建", "海南", "浙江", "山东", "江苏", "辽宁", "河北")
        if name in (record.visible_answer or "")
    }
    if q_provinces and a_provinces and not (q_provinces & a_provinces):
        return [Finding(record.id, "D10", "S1", f"问{q_provinces}答{a_provinces}", chunk_id="")]
    return []


def d11(record: AuditRecord, doc_meta: dict[str, dict[str, Any]]) -> list[Finding]:
    if record.abstained:
        return []
    versioned = [
        str(cite.get("doc_id", ""))
        for cite in record.citations
        if doc_meta.get(str(cite.get("doc_id", "")), {}).get("effective_from")
        or doc_meta.get(str(cite.get("doc_id", "")), {}).get("year")
    ]
    if not versioned:
        return []
    text = record.visible_answer or ""
    if not any(word in text for word in ("现行", "修订", "版", "施行", "生效", "年")):
        if not re.search(r"(?:19|20)\d{2}", text):
            return [
                Finding(record.id, "D11", "S3", "引用版本文档但无时效声明", chunk_id=versioned[0])
            ]
    return []


def run_all(
    record: AuditRecord,
    chunk_index: dict[str, list[tuple[str, str]]],
    doc_meta: dict[str, dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[Finding]:
    chunks = _texts_for(record, chunk_index)
    cited = _cited_texts(record, chunk_index)
    findings: list[Finding] = []
    findings += d1(record, chunks)
    findings += d2(record)
    findings += d3(record)
    findings += d4(record)
    findings += d5(record, chunks)
    findings += d6(record)
    findings += d7(record, chunk_index)
    findings += d8(record, doc_meta)
    findings += d9(record, cited)
    findings += d10(record)
    findings += d11(record, doc_meta)
    return findings
