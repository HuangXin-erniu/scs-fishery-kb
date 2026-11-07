"""Deterministic point terms for acceptance scoring.

The private instrument states required points in prose. Scoring them needs a
stable, auditable rule, so a point is reduced to anchors: numbers with units,
quoted titles, document numbers and domain concepts. Points without anchors are
reported as ``needs_review`` instead of being scored as hits or misses.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

NUMBER_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:年|月|日|时|天|小时|分钟|米|厘米|毫米|公里|海里|吨|公斤|千克|"
    r"千元|万元|亿元|元|%|‰|个月|次|人|艘|台|个|级|类|度|分|秒|成|倍|尾|份|项|条|款|号)?"
)
SIGN_MAP = str.maketrans({"°": "度", "′": "分", "″": "秒", "℃": "度"})
QUOTE_RE = re.compile(r"《[^》]{2,40}》")
DOCNO_RE = re.compile(r"[\u4e00-\u9fa5A-Za-z]{0,12}〔\d{4}〕\s*\d+\s*号")
GENERIC_CONCEPTS = {
    "渔业",
    "船舶",
    "管理",
    "规定",
    "办法",
    "标准",
    "要求",
    "水域",
    "海域",
    "海洋",
    "中国",
    "国家",
    "部门",
    "机构",
    "系统",
    "数据",
    "信息",
    "服务",
    "情况",
    "问题",
    "地方",
    "以上",
}


def normalize(text: str) -> str:
    """Fold width, degree symbols and whitespace so values compare directly."""
    folded = unicodedata.normalize("NFKC", str(text)).translate(SIGN_MAP)
    return "".join(folded.split())


@dataclass(frozen=True)
class PointSpec:
    terms: tuple[str, ...]
    mode: str = "section"
    skip: bool = False
    note: str = ""


@dataclass
class ConceptSource:
    """Domain concepts used as anchors, loaded from public configuration."""

    concepts: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def load(cls, terms_path: Path | str, extra_path: Path | str | None = None) -> ConceptSource:
        import yaml

        found: set[str] = set()
        terms_file = Path(terms_path).expanduser()
        if terms_file.is_file():
            data = yaml.safe_load(terms_file.read_text(encoding="utf-8")) or {}
            for term in data.get("terms") or []:
                if term.get("status") not in (None, "approved"):
                    continue
                for name in [term.get("standard"), *(term.get("variants") or [])]:
                    text = normalize(str(name or ""))
                    if len(text) >= 2 and text not in GENERIC_CONCEPTS:
                        found.add(text)
        if extra_path:
            extra_file = Path(extra_path).expanduser()
            if extra_file.is_file():
                data = yaml.safe_load(extra_file.read_text(encoding="utf-8")) or {}
                for name in data.get("terms") or []:
                    text = normalize(str(name or ""))
                    if len(text) >= 2 and text not in GENERIC_CONCEPTS:
                        found.add(text)
        ordered = tuple(sorted(found, key=lambda item: (-len(item), item)))
        return cls(concepts=ordered)

    def matches(self, text: str, limit: int = 3) -> list[str]:
        """Return the longest non-overlapping concepts present in ``text``."""
        normalized = normalize(text)
        found: list[str] = []
        occupied: list[tuple[int, int]] = []
        for concept in self.concepts:
            start = normalized.find(concept)
            if start < 0:
                continue
            end = start + len(concept)
            if any(start < right and left < end for left, right in occupied):
                continue
            found.append(concept)
            occupied.append((start, end))
            if len(found) >= limit:
                break
        return found


@dataclass
class PointOverrides:
    """Private per-point overrides for points the automatic rule cannot score."""

    specs: dict[tuple[str, int], PointSpec] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | str | None) -> PointOverrides:
        import yaml

        if not path:
            return cls()
        override_path = Path(path).expanduser()
        if not override_path.is_file():
            return cls()
        data = yaml.safe_load(override_path.read_text(encoding="utf-8")) or {}
        specs: dict[tuple[str, int], PointSpec] = {}
        for identifier, items in (data.get("points") or {}).items():
            for index, item in enumerate(items or []):
                if not isinstance(item, dict):
                    raise ValueError(f"override {identifier}[{index}] must be an object")
                terms = item.get("terms")
                specs[(str(identifier), int(item.get("index", index)))] = PointSpec(
                    terms=tuple(normalize(str(term)) for term in (terms or [])),
                    mode=str(item.get("mode") or "section"),
                    skip=bool(item.get("skip")),
                    note=str(item.get("note") or ""),
                )
        return cls(specs=specs)

    def get(self, identifier: str, index: int) -> PointSpec | None:
        return self.specs.get((identifier, index))


def derive_terms(
    point_text: str,
    *,
    concepts: ConceptSource,
    override: PointSpec | None = None,
    max_terms: int = 3,
) -> PointSpec:
    """Reduce one required point to anchors and a matching mode."""
    if override is not None and (override.terms or override.skip):
        mode = override.mode or "section"
        return PointSpec(terms=override.terms, mode=mode, skip=override.skip, note=override.note)

    text = normalize(point_text)
    numbers = [match.group(0) for match in NUMBER_RE.finditer(text) if match.group(0)]
    quoted = [match.group(0) for match in QUOTE_RE.finditer(text)]
    docnos = [match.group(0) for match in DOCNO_RE.finditer(text)]
    strong = _dedupe([*numbers, *quoted, *docnos])
    if strong:
        return PointSpec(terms=tuple(strong[: max(1, max_terms + 1)]), mode="section")
    found = concepts.matches(text, limit=max_terms)
    if found:
        mode = "section" if len(found) <= 2 else "document"
        return PointSpec(terms=tuple(found), mode=mode)
    return PointSpec(terms=(), mode="section", note="no anchor derived")


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def point_specs(
    row: dict[str, Any],
    *,
    concepts: ConceptSource,
    overrides: PointOverrides,
    max_terms: int = 3,
) -> list[PointSpec]:
    """Derive the spec for every required point of one question."""
    specs: list[PointSpec] = []
    for index, point in enumerate(row.get("required_points") or []):
        override = overrides.get(str(row.get("id")), index)
        specs.append(
            derive_terms(str(point), concepts=concepts, override=override, max_terms=max_terms)
        )
    return specs
