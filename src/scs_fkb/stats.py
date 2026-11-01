from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from .bm25 import BM25Index
from .config import data_root as default_data_root
from .models import Chunk
from .text import tokenize

DEFAULT_TABLE = Path("statistics") / "core-indicators-v3.csv"
COLUMNS = (
    "data_year",
    "edition",
    "type",
    "region",
    "sea_area",
    "gear",
    "operation_type",
    "power_band",
    "length_band",
    "species",
    "indicator",
    "value",
    "unit",
    "basis",
    "table_id",
    "table_name",
    "source_file",
    "sheet",
    "row",
    "source_sha256",
)

INDICATOR_NAMES = {
    "capture_production": "海洋捕捞产量",
    "capture_production_sea_area": "海洋捕捞产量（按海域分）",
    "capture_production_gear": "海洋捕捞产量（按渔具分）",
    "capture_production_species": "海洋捕捞产量（按品种分）",
    "vessel_count": "海洋捕捞机动渔船数量",
    "vessel_gross_tonnage": "海洋捕捞机动渔船总吨位",
    "vessel_kilowatts": "海洋捕捞机动渔船功率",
    "marine_fishery_population": "海洋渔业人口",
    "traditional_fishers": "传统渔民",
    "marine_fishery_employment": "海洋渔业从业人员",
    "capture_employment": "海洋捕捞从业人员",
    "marine_capture_output_value": "海洋捕捞产值",
    "coastal_central_fishing_port": "沿海中心渔港",
    "coastal_class1_fishing_port": "沿海一级渔港",
    "coastal_class2_fishing_port": "沿海二级渔港",
    "coastal_class3_fishing_port": "沿海三级渔港",
    "coastal_unrated_fishing_port": "沿海未评级渔港",
}

UNIT_NAMES = {
    "ton": "吨",
    "vessel": "艘",
    "gross_ton": "总吨",
    "kilowatt": "千瓦",
    "person": "人",
    "ten_thousand_yuan": "万元",
    "count": "个",
}

REGION_NAMES = {
    "China": "全国",
    "Guangdong": "广东",
    "Guangxi": "广西",
    "Hainan": "海南",
    "Fujian": "福建",
}

SEA_NAMES = {"South China Sea": "南海区"}

GEAR_NAMES = {
    "trawl": "拖网",
    "purse_seine": "围网",
    "gillnet": "刺网",
    "stow_net": "张网",
    "hook": "钓具",
    "other": "其他",
}

DERIVED_BASIS = ("three_province_subtotal", "difference")

REGION_ALIASES = {
    "全国": "China",
    "中国": "China",
    "广东": "Guangdong",
    "广东省": "Guangdong",
    "广西": "Guangxi",
    "广西壮族自治区": "Guangxi",
    "海南": "Hainan",
    "海南省": "Hainan",
    "福建": "Fujian",
    "福建省": "Fujian",
}

SEA_ALIASES = {
    "南海区": "South China Sea",
    "南海海域": "South China Sea",
    "南海": "South China Sea",
}

GEAR_ALIASES = {
    "拖网": "trawl",
    "围网": "purse_seine",
    "刺网": "gillnet",
    "张网": "stow_net",
    "钓具": "hook",
    "钓业": "hook",
    "其他": "other",
}

INDICATOR_CUES = {
    "捕捞产量": ("production",),
    "产量": ("production",),
    "船数": ("vessel_count",),
    "渔船数量": ("vessel_count",),
    "渔船艘数": ("vessel_count",),
    "机动渔船": ("vessel_count",),
    "总吨": ("tonnage",),
    "总吨位": ("tonnage",),
    "千瓦": ("power",),
    "功率": ("power",),
    "渔民": ("population",),
    "从业人员": ("employment",),
    "劳动力": ("employment",),
    "产值": ("value",),
    "渔港": ("port",),
}

GROUP_MAP = {
    "production": (
        "capture_production",
        "capture_production_sea_area",
        "capture_production_gear",
        "capture_production_species",
    ),
    "vessel_count": ("vessel_count",),
    "tonnage": ("vessel_gross_tonnage",),
    "power": ("vessel_kilowatts",),
    "population": ("marine_fishery_population", "traditional_fishers"),
    "employment": ("marine_fishery_employment", "capture_employment"),
    "value": ("marine_capture_output_value",),
    "port": (
        "coastal_central_fishing_port",
        "coastal_class1_fishing_port",
        "coastal_class2_fishing_port",
        "coastal_class3_fishing_port",
        "coastal_unrated_fishing_port",
    ),
}

TREND_MARKERS = ("趋势", "历年", "逐年", "变化")


class StatsError(RuntimeError):
    """Raised when the local indicator table is missing or malformed."""


@dataclass
class StatsHit:
    row: dict[str, str]
    text: str
    citation: str
    score: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "citation": self.citation,
            "score": round(self.score, 6),
            "notes": self.notes,
            "data_year": self.row["data_year"],
            "indicator": self.row["indicator"],
        }


def table_path(root: Path | str | None = None) -> Path:
    base = Path(root) if root else default_data_root()
    return base / DEFAULT_TABLE


@lru_cache(maxsize=4)
def _load(path: str) -> tuple[dict[str, str], ...]:
    table = Path(path)
    if not table.is_file():
        raise StatsError(f"statistics table not found: {table}")
    with table.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise StatsError("statistics table columns do not match the schema")
        rows = tuple(row for row in reader)
    if not rows:
        raise StatsError("statistics table is empty")
    return rows


@lru_cache(maxsize=4)
def _index(path: str) -> BM25Index:
    rows = _load(path)
    chunks = []
    for index, row in enumerate(rows):
        chunks.append(
            Chunk(
                chunk_id=f"stats-{index}",
                doc_id=f"STAT-YB-{row['edition']}",
                source_id=f"STAT-YB-{row['edition']}",
                page=0,
                section=row["table_name"],
                text=_sentence(row),
                token_count=len(tokenize(_sentence(row))),
                char_start=0,
                char_end=len(_sentence(row)),
                sensitivity="internal",
            )
        )
    return BM25Index(chunks)


def _place(row: dict[str, str]) -> str:
    region = REGION_NAMES.get(row["region"], row["region"])
    sea = SEA_NAMES.get(row["sea_area"], row["sea_area"])
    if region and sea:
        return f"{region}（{sea}列）"
    if region:
        return region
    return sea or "全国"


def _sentence(row: dict[str, str]) -> str:
    label = INDICATOR_NAMES.get(row["indicator"], row["indicator"])
    parts = [f"{row['data_year']}年", _place(row), label]
    if row["gear"]:
        parts.append(f"{GEAR_NAMES.get(row['gear'], row['gear'])}类渔具")
    if row["operation_type"]:
        parts.append(f"{GEAR_NAMES.get(row['operation_type'], row['operation_type'])}作业")
    if row["species"]:
        parts.append(row["species"])
    unit = UNIT_NAMES.get(row["unit"], row["unit"])
    parts.append(f"{_format_value(row['value'])}{unit}" if row["value"] else "未刊出")
    parts.append(f"（{row['edition']}年版 {row['table_name']}，{row['basis']}）")
    return " ".join(parts)


def _format_value(value: str) -> str:
    try:
        number = float(value)
    except ValueError:
        return value
    return str(int(number)) if number.is_integer() else f"{number:g}"


def _citation(row: dict[str, str]) -> str:
    table = row["table_name"].strip()
    return f"[STAT-YB-{row['edition']} §{table}]"


def _notes(row: dict[str, str]) -> list[str]:
    notes = []
    if row["basis"] == "published_south_sea":
        notes.append("南海列在 2017–2020 年含福建，2021 年起不含福建。")
    if row["data_year"] == "2025":
        notes.append("2025 年为扫描件抽样值，非全表。")
    return notes


def _canonical(text: str, aliases: dict[str, str]) -> str | None:
    for alias in sorted(aliases, key=len, reverse=True):
        if alias in text:
            return aliases[alias]
    return None


def parse_query(text: str) -> dict[str, Any]:
    years = [int(year) for year in re.findall(r"(20(?:1[7-9]|2[0-5]))\s*年?", text)]
    groups: list[str] = []
    for cue in sorted(INDICATOR_CUES, key=len, reverse=True):
        if cue in text and INDICATOR_CUES[cue][0] not in groups:
            groups.append(INDICATOR_CUES[cue][0])
    return {
        "years": sorted(set(years)),
        "region": _canonical(text, REGION_ALIASES),
        "sea_area": _canonical(text, SEA_ALIASES),
        "gear": _canonical(text, GEAR_ALIASES),
        "groups": groups,
        "trend": any(marker in text for marker in TREND_MARKERS),
    }


def _indicators(groups: list[str]) -> tuple[str, ...]:
    if not groups:
        return ()
    result: list[str] = []
    for group in groups:
        for indicator in GROUP_MAP[group]:
            if indicator not in result:
                result.append(indicator)
    return tuple(result)


def _matches(
    row: dict[str, str],
    parsed: dict[str, Any],
    allowed: tuple[str, ...],
    ignore_gear: bool = False,
    ignore_sea: bool = False,
) -> bool:
    if allowed and row["indicator"] not in allowed:
        return False
    if parsed["years"] and int(row["data_year"]) not in parsed["years"]:
        return False
    if parsed["region"] and row["region"] != parsed["region"]:
        return False
    if not ignore_sea and parsed["sea_area"] and row["sea_area"] != parsed["sea_area"]:
        return False
    if not ignore_gear and parsed["gear"]:
        if parsed["gear"] not in (row["gear"], row["operation_type"]):
            return False
    return True


def query(text: str, top_k: int = 8, root: Path | str | None = None) -> list[StatsHit]:
    path = table_path(root)
    rows = _load(str(path))
    parsed = parse_query(text)
    allowed = _indicators(parsed["groups"])

    selected = [row for row in rows if _matches(row, parsed, allowed)]
    signals = (
        parsed["years"],
        parsed["region"],
        parsed["sea_area"],
        parsed["gear"],
        parsed["groups"],
    )
    if not any(signals):
        return []
    relaxed: list[str] = []
    if not selected and parsed["gear"]:
        relaxed.append("gear")
        without_gear = [row for row in rows if _matches(row, parsed, allowed, ignore_gear=True)]
        selected = without_gear
    if not selected and parsed["sea_area"]:
        relaxed.append("sea_area")
        without_sea = [row for row in rows if _matches(row, parsed, allowed, ignore_sea=True)]
        selected = without_sea
    if not selected:
        index = _index(str(path))
        hits = index.search(text, top_k=top_k)
        result = []
        for hit in hits:
            row = rows[int(hit.chunk.chunk_id.split("-")[1])]
            result.append(
                StatsHit(
                    row=row,
                    text=_sentence(row),
                    citation=_citation(row),
                    score=hit.score,
                    notes=_notes(row),
                )
            )
        return result

    if "差值" not in text and "小计" not in text and "合计" not in text:
        selected = [row for row in selected if row["basis"] not in DERIVED_BASIS]
    seen: set[tuple[str, str, str, str, str]] = set()
    unique = []
    for row in selected:
        key = (
            row["data_year"],
            row["region"],
            row["gear"],
            row["operation_type"],
            row["indicator"],
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    selected = unique
    if not parsed["years"] and not parsed["trend"]:
        latest = max(int(row["data_year"]) for row in selected)
        selected = [row for row in selected if int(row["data_year"]) == latest]

    selected.sort(
        key=lambda row: (
            int(row["data_year"]) if parsed["trend"] else -int(row["data_year"]),
            row["region"],
            row["gear"],
            row["operation_type"],
        )
    )
    hits = [
        StatsHit(row=row, text=_sentence(row), citation=_citation(row), notes=_notes(row))
        for row in selected[:top_k]
    ]

    gap = _gap_note(parsed, relaxed)
    if gap and hits:
        hits[0].notes = [*hits[0].notes, gap]
    return hits


def _gap_note(parsed: dict[str, Any], relaxed: list[str]) -> str | None:
    groups = parsed["groups"]
    if "production" in groups and parsed["gear"] and parsed["sea_area"]:
        return (
            "年鉴未刊出按作业类型分的海域产量：海域产量与按渔具分产量分属不同表，此处按海域列出。"
        )
    if "production" in groups and parsed["gear"] and "gear" in relaxed:
        return "年鉴未刊出按作业类型分的海域产量，此处只按海域列出。"
    if "vessel_count" in groups and parsed["sea_area"] and "sea_area" in relaxed:
        return "年鉴船数表无海域维度，只有省份与作业类型；此处返回省级船数。"
    return None
