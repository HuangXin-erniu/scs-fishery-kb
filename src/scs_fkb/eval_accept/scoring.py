"""Deterministic scoring for the private acceptance instrument.

Metric names and pass lines follow the instrument's protocol: point coverage,
citation accuracy, misanswer rate, refusal-with-channel rate, as-of declaration
rate and basis (measurement basis) accuracy, plus latency. Every score is
derived from the answer text and its citations; unjudgeable rows are reported
separately instead of being counted as passes or failures.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from typing import Any

from ..coverage import point_status
from .points import NUMBER_RE, PointOverrides, PointSpec, normalize, point_specs

DOCNO_RE = re.compile(r"[\u4e00-\u9fa5A-Za-z]{0,12}〔\d{4}〕\s*\d+\s*号")
ENTITY_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:万元|亿元|元|%|％|‰|天|个月|小时|公斤|千克|吨|海里|米)")
CHANNEL_RE = re.compile(
    r"咨询|办理|申办|申报|报备|备案|主管部门|渔业主管部门|渔政|海事|海警|官网|办事窗口|"
    r"属地|县级以上|省级|市级|农业农村部|自然资源部|交通运输部|外事|大使馆|领事馆|"
    r"保护区管理机构|联系电话|服务窗口"
)
REFUSAL_RE = re.compile(
    r"无法|不足以|未收录|未登记|超出|不掌握|建议咨询|请咨询|以官方发布|需核实|不能确定|没有依据|尚无依据"
)
VERSION_RE = re.compile(r"20\d{2}\s*年\s*[^。；]{0,16}(?:版|修订|施行|生效|通告|公告|规定|办法)")
BASIS_RE = re.compile(
    r"全国|南海|海区|分区|分省|年度|年均|单次|航次|重量|尾数|表\s*\d|图\s*\d|条|款"
)
UNREGISTERED = "未登记"


@dataclass
class ScoringConfig:
    """Thresholds and matching knobs used by the acceptance scorer."""

    thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "misanswer_rate": 0.10,
            "citation_accuracy": 0.90,
            "point_coverage": 0.80,
            "refusal_channel_rate": 0.90,
            "asof_declaration_rate": 0.90,
            "basis_accuracy": 0.85,
        }
    )
    point_threshold_full: float = 0.80
    point_threshold_partial: float = 0.50
    location_min_overlap: int = 3
    max_terms: int = 3

    @classmethod
    def from_config(cls, data: dict[str, Any]) -> ScoringConfig:
        thresholds = dict(cls().thresholds)
        raw = data.get("thresholds") or {}
        for name, spec in raw.items():
            if isinstance(spec, dict):
                bound = spec.get("max", spec.get("min"))
            else:
                bound = spec
            if bound is not None:
                thresholds[name] = float(bound)
        scoring = data.get("scoring") or {}
        return cls(
            thresholds=thresholds,
            point_threshold_full=float(scoring.get("point_threshold_full", 0.80)),
            point_threshold_partial=float(scoring.get("point_threshold_partial", 0.50)),
            location_min_overlap=int(scoring.get("location_min_overlap", 3)),
            max_terms=int(scoring.get("max_terms", 3)),
        )


def _clean(text: str) -> str:
    return re.sub(r"[\s·、，,；;：:（）()《》〈〉“”\"'\-—–_/]+", "", normalize(text))


def longest_common_substring(left: str, right: str) -> int:
    """Length of the longest common substring, used for loose location matching."""
    if not left or not right:
        return 0
    best = 0
    previous = [0] * (len(right) + 1)
    for left_char in left:
        current = [0] * (len(right) + 1)
        for index, right_char in enumerate(right, start=1):
            if left_char == right_char:
                current[index] = previous[index - 1] + 1
                best = max(best, current[index])
        previous = current
    return best


def _requirement_locations(row: dict[str, Any]) -> list[str]:
    requirement = str(row.get("citation_requirement") or "")
    tail = ""
    for separator in ("｜", "|"):
        if separator in requirement:
            tail = requirement.split(separator, 1)[1]
            break
    locations: list[str] = []
    for part in re.split(r"[；;]", tail) if tail else []:
        part = part.strip()
        if not part:
            continue
        locations.append(part.split("·", 1)[1] if "·" in part else part)
    if not locations:
        locations = [str(item) for item in row.get("doc_locations") or []]
    return locations


def _citation_view(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return dict(item)


def _cited_scs(
    citations: list[dict[str, Any]],
    docmap: Any,
) -> list[tuple[str, str]]:
    """Return (instrument id, cover kind) for every citation that maps to one."""
    found: list[tuple[str, str]] = []
    for citation in citations:
        doc_id = str(citation.get("doc_id") or "")
        for scs_id in docmap.scs_for_doc(doc_id):
            found.append((scs_id, docmap.covers(scs_id)))
    return found


def _location_ok(
    answer: str,
    citations: list[dict[str, Any]],
    row: dict[str, Any],
    docmap: Any,
    minimum: int,
    terms: list[str],
) -> tuple[bool, list[str]]:
    locations = _requirement_locations(row)
    if not locations:
        return True, []
    expected = {item for item in row.get("scs_doc_ids") or []}
    needles = [_clean(location) for location in locations]
    best = 0
    for citation in citations:
        doc_id = str(citation.get("doc_id") or "")
        if not set(docmap.scs_for_doc(doc_id)) & expected:
            continue
        section = _clean(str(citation.get("section") or ""))
        page = citation.get("page")
        for location, needle in zip(locations, needles, strict=False):
            if page and str(page) in location:
                return True, []
            best = max(best, longest_common_substring(needle, section))
    if best >= minimum:
        return True, []
    # The instrument states locations as topic labels ("许可证有效期"), which a
    # clause-numbered section title rarely repeats. A cited clause that carries
    # one of the question's own required anchors still counts as located.
    expected_terms = [normalize(term) for term in terms if term]
    if expected_terms:
        for key, text in _cited_groups(answer, citations):
            if not set(docmap.scs_for_doc(key[0])) & expected:
                continue
            haystack = normalize(text)
            if any(term in haystack for term in expected_terms):
                return True, []
    return False, [f"location_unmatched:{locations[0]}"]


def _entity_claim(answer: str) -> bool:
    text = normalize(answer)
    return bool(ENTITY_RE.search(text) or DOCNO_RE.search(text))


def _has_channel(answer: str) -> bool:
    return bool(CHANNEL_RE.search(normalize(answer)))


def _declares_version(answer: str) -> bool:
    text = normalize(answer)
    return bool(VERSION_RE.search(text) or DOCNO_RE.search(text))


def _basis_tokens(answer: str) -> bool:
    return bool(BASIS_RE.search(normalize(answer)))


CITATION_GROUP_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_-]*)(?: p\.(\d+))?(?: §([^\]]+))?\]")
SENTENCE_SPLIT = re.compile(r"(?<=[。！？；])|\n+")


def _cited_groups(
    answer: str, citations: list[dict[str, Any]]
) -> list[tuple[tuple[str, str], str]]:
    """Group answer sentences per citation and append the cited section title.

    Section titles frequently carry the point label itself (for example
    "二、休渔作业类型"), so they belong to the cited evidence even when the
    sentence paraphrases the label.
    """
    sentences = [part.strip() for part in SENTENCE_SPLIT.split(answer) if part.strip()]
    groups: dict[tuple[str, str], list[str]] = {}
    for sentence in sentences:
        for match in CITATION_GROUP_RE.finditer(sentence):
            key = (match.group(1), (match.group(3) or "").strip())
            groups.setdefault(key, []).append(sentence)
    for citation in citations:
        key = (str(citation.get("doc_id") or ""), str(citation.get("section") or ""))
        groups.setdefault(key, [])
    return [(key, " ".join(texts) + " " + key[1]) for key, texts in groups.items()]


def _point_covered(
    answer: str,
    citations: list[dict[str, Any]],
    spec: PointSpec,
) -> bool:
    terms = [normalize(term) for term in spec.terms if term]
    if not terms:
        return False
    covered, _missing = point_status(answer, {"terms": terms, "mode": spec.mode or "section"})
    if covered:
        return True
    groups = _cited_groups(answer, citations)
    for _key, text in groups:
        haystack = normalize(text)
        if all(term in haystack for term in terms):
            return True
    if spec.mode == "document":
        by_doc: dict[str, list[str]] = {}
        for (doc_id, _section), text in groups:
            by_doc.setdefault(doc_id, []).append(text)
        for texts in by_doc.values():
            haystack = normalize(" ".join(texts))
            if all(term in haystack for term in terms):
                return True
    return False


def score_row(
    row: dict[str, Any],
    result: dict[str, Any],
    *,
    docmap: Any,
    concepts: Any,
    overrides: PointOverrides,
    config: ScoringConfig,
) -> dict[str, Any]:
    """Score one question against its answer and citations."""
    answer = str(result.get("answer") or "")
    citations = [_citation_view(item) for item in result.get("citations") or []]
    answered = not bool(result.get("abstained"))
    answerability = str(row.get("answerability") or "")
    dimension = str(row.get("dimension") or "")
    flags: list[str] = []

    expected = [item for item in row.get("scs_doc_ids") or [] if item != UNREGISTERED]
    specs = point_specs(
        row,
        concepts=concepts,
        overrides=overrides,
        max_terms=config.max_terms,
    )
    anchor_terms = [term for spec in specs for term in spec.terms]
    cited = _cited_scs(citations, docmap)
    hit_ids = sorted({scs_id for scs_id, _cover in cited if scs_id in expected})
    partial_cover = any(cover == "partial" for scs_id, cover in cited if scs_id in expected)
    if not citations:
        flags.append("citation_none")
    citation_accuracy: bool | None
    if not expected:
        citation_accuracy = None
        flags.append("no_expected_document")
    elif not citations and not answered:
        citation_accuracy = None
        flags.append("citation_none")
    elif not citations:
        citation_accuracy = False
    else:
        doc_hit = bool(hit_ids)
        location_ok, location_flags = _location_ok(
            answer, citations, row, docmap, config.location_min_overlap, anchor_terms
        )
        flags.extend(location_flags)
        citation_accuracy = doc_hit and location_ok
        if not doc_hit:
            flags.append("wrong_document")
    if partial_cover:
        flags.append("partial_cover")

    hits = 0
    judgeable = 0
    skipped = 0
    points = row.get("required_points") or []
    for _point, spec in zip(points, specs, strict=False):
        if spec.skip:
            skipped += 1
            continue
        if not spec.terms:
            flags.append("point_needs_review")
            continue
        judgeable += 1
        if _point_covered(answer, citations, spec):
            hits += 1
    point_coverage = hits / judgeable if judgeable else None

    misanswer: bool | None = None
    correct_refusal: bool | None = None
    if answerability == "应拒答":
        entity = _entity_claim(answer) if answered else False
        channel = _has_channel(answer)
        refusal_style = bool(REFUSAL_RE.search(normalize(answer))) if answered else False
        misanswer = bool(answered and not (refusal_style and channel))
        correct_refusal = bool((not answered or refusal_style) and channel)
        if not answered and not channel:
            flags.append("refusal_without_channel")
        if answered and refusal_style and not channel:
            flags.append("non_committal")
        if answered and not refusal_style and not entity:
            flags.append("answered_out_of_scope")
    refusal_rate_row = correct_refusal

    asof_declared: bool | None = None
    if dimension == "时效冲突":
        asof_declared = _declares_version(answer)
        if not asof_declared:
            flags.append("no_version_declaration")

    basis_score: float | None = None
    if dimension == "数值召回":
        anchors: list[str] = []
        for item in row.get("numeric_anchors") or []:
            if not str(item).strip():
                continue
            anchors.extend(token for token in NUMBER_RE.findall(normalize(item)) if token)
        if not anchors:
            anchors = [
                normalize(spec.terms[0])
                for spec in specs
                if spec.terms and NUMBER_RE.search(spec.terms[0])
            ]
        text = normalize(answer)
        if anchors:
            present = [anchor for anchor in anchors if anchor and anchor in text]
            if len(present) == len(anchors):
                basis_score = 1.0 if _basis_tokens(answer) else 0.5
                if basis_score == 0.5:
                    flags.append("basis_missing")
            else:
                basis_score = 0.0
                flags.append("anchor_missing")
        else:
            flags.append("no_numeric_anchor")

    band: float | None
    if answerability == "应拒答":
        if misanswer:
            band = 0.0
        elif correct_refusal:
            band = 1.0
        else:
            band = 0.5
    elif answerability == "可答":
        if not answered:
            band = 0.0
        elif point_coverage is None:
            band = None
        elif point_coverage >= config.point_threshold_full and citation_accuracy:
            band = 1.0
        elif point_coverage >= config.point_threshold_partial or citation_accuracy:
            band = 0.5
        else:
            band = 0.0
        if dimension == "时效冲突" and not asof_declared:
            band = 0.0
        elif dimension == "数值召回" and basis_score is not None:
            band = min(band, basis_score)
    else:
        band = None
        if answered and _has_channel(answer) and not _entity_claim(answer):
            flags.append("partial_with_channel")

    if answered and skipped:
        flags.append("points_skipped")

    return {
        "id": row.get("id"),
        "split": row.get("split"),
        "answerability": answerability,
        "dimension": dimension,
        "domain": row.get("domain"),
        "persona": row.get("persona"),
        "sea_area": row.get("sea_area"),
        "abstained": bool(result.get("abstained")),
        "reason": str(result.get("reason") or ""),
        "mode": str(result.get("mode") or ""),
        "latency_ms": int(result.get("latency_ms") or 0),
        "answer": answer,
        "citation_docs": [str(item.get("doc_id") or "") for item in citations],
        "citation_sections": [str(item.get("section") or "") for item in citations],
        "citation_hit": bool(hit_ids) if expected else None,
        "citation_accuracy": citation_accuracy,
        "point_coverage": point_coverage,
        "points_hit": hits,
        "points_judgeable": judgeable,
        "points_skipped": skipped,
        "misanswer": misanswer,
        "correct_refusal": refusal_rate_row,
        "asof_declared": asof_declared,
        "basis_score": basis_score,
        "band": band,
        "flags": sorted(set(flags)),
        "error": str(result.get("error") or ""),
    }


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _p95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
    return ordered[index]


def aggregate(scored: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate scored rows into protocol metrics."""
    answered = [row for row in scored if not row["abstained"]]
    citations = [row for row in scored if row["citation_accuracy"] is not None]
    refusals = [row for row in scored if row["answerability"] == "应拒答"]
    asof = [row for row in scored if row["asof_declared"] is not None]
    basis = [row for row in scored if row["basis_score"] is not None]
    points = [row for row in scored if row["point_coverage"] is not None]
    bands = [row["band"] for row in scored if row["band"] is not None]
    judgeable_points = sum(row["points_judgeable"] for row in scored)
    review_rows = sum(1 for row in scored if "point_needs_review" in row["flags"])
    return {
        "questions": len(scored),
        "answered": len(answered),
        "answer_rate": round(len(answered) / len(scored), 4) if scored else None,
        "point_coverage": _mean([row["point_coverage"] for row in points]),
        "point_rows": len(points),
        "judgeable_points": judgeable_points,
        "rows_with_unjudgeable_points": review_rows,
        "citation_accuracy": _mean([1.0 if row["citation_accuracy"] else 0.0 for row in citations]),
        "citation_rows": len(citations),
        "citation_coverage": (
            round(len([row for row in answered if row["citation_docs"]]) / len(answered), 4)
            if answered
            else None
        ),
        "misanswer_rate": (
            round(len([row for row in refusals if row["misanswer"]]) / len(refusals), 4)
            if refusals
            else None
        ),
        "refusal_rows": len(refusals),
        "refusal_channel_rate": (
            round(len([row for row in refusals if row["correct_refusal"]]) / len(refusals), 4)
            if refusals
            else None
        ),
        "asof_declaration_rate": (
            round(len([row for row in asof if row["asof_declared"]]) / len(asof), 4)
            if asof
            else None
        ),
        "asof_rows": len(asof),
        "basis_accuracy": _mean([row["basis_score"] for row in basis]),
        "basis_rows": len(basis),
        "band_mean": _mean([float(value) for value in bands]),
        "band_rows": len(bands),
        "latency_mean_ms": _mean([row["latency_ms"] for row in scored]),
        "latency_p95_ms": _p95([row["latency_ms"] for row in scored]),
    }


GROUP_FIELDS = {
    "domain": "domain",
    "persona": "persona",
    "sea_area": "sea_area",
    "dimension": "dimension",
    "answerability": "answerability",
}


def group_metrics(scored: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """Aggregate by the dimensions the instrument reports on."""
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for name, attribute in GROUP_FIELDS.items():
        buckets: dict[str, list[dict[str, Any]]] = {}
        for row in scored:
            buckets.setdefault(str(row.get(attribute) or ""), []).append(row)
        grouped[name] = {key: aggregate(rows) for key, rows in sorted(buckets.items()) if key}
    return grouped


def gate_result(metrics: dict[str, Any], thresholds: dict[str, float]) -> dict[str, Any]:
    """Compare overall metrics with the protocol pass lines."""
    limits = {
        "misanswer_rate": ("max", thresholds.get("misanswer_rate", 0.10)),
        "citation_accuracy": ("min", thresholds.get("citation_accuracy", 0.90)),
        "point_coverage": ("min", thresholds.get("point_coverage", 0.80)),
        "refusal_channel_rate": ("min", thresholds.get("refusal_channel_rate", 0.90)),
        "asof_declaration_rate": ("min", thresholds.get("asof_declaration_rate", 0.90)),
        "basis_accuracy": ("min", thresholds.get("basis_accuracy", 0.85)),
    }
    checks: dict[str, Any] = {}
    failures: list[str] = []
    for name, (kind, threshold) in limits.items():
        value = metrics.get(name)
        if value is None:
            checks[name] = {"value": None, "threshold": threshold, "passed": False}
            failures.append(f"{name}: no measurable rows")
            continue
        passed = value <= threshold if kind == "max" else value >= threshold
        checks[name] = {
            "value": value,
            "threshold": threshold,
            "operator": kind,
            "passed": passed,
        }
        if not passed:
            failures.append(f"{name}: {value} {'>' if kind == 'max' else '<'} {threshold}")
    return {"passed": not failures, "checks": checks, "failures": failures}


def reason_clusters(scored: list[dict[str, Any]], limit: int = 15) -> list[dict[str, Any]]:
    """Count failure flags and answer reasons across rows."""
    flag_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    for row in scored:
        for flag in row["flags"]:
            key = flag.split(":", 1)[0]
            flag_counts[key] = flag_counts.get(key, 0) + 1
        reason = row["reason"] or "unknown"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    clusters = [
        {"kind": "flag", "name": name, "count": count}
        for name, count in sorted(flag_counts.items(), key=lambda item: -item[1])
    ]
    clusters += [
        {"kind": "reason", "name": name, "count": count}
        for name, count in sorted(reason_counts.items(), key=lambda item: -item[1])
    ]
    return clusters[:limit]


def latency_summary(scored: list[dict[str, Any]]) -> dict[str, Any]:
    values = [row["latency_ms"] for row in scored]
    if not values:
        return {"mean": None, "median": None, "p95": None}
    return {
        "mean": round(statistics.fmean(values), 2),
        "median": statistics.median(values),
        "p95": _p95(values),
    }
