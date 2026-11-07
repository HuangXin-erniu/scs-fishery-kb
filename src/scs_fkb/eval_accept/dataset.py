from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "id",
    "persona",
    "sea_area",
    "question",
    "domain",
    "domain_code",
    "answerability",
    "required_points",
    "dimension",
    "scs_doc_ids",
    "split",
)
ANSWERABILITY = ("可答", "部分可答", "应拒答")
DIMENSIONS = ("数值召回", "时效冲突", "多跳推断", "单点事实")
SPLITS = ("dev", "holdout")


class DatasetError(ValueError):
    """Raised when the private acceptance dataset is missing or malformed."""


def load_dataset(path: Path | str) -> list[dict[str, Any]]:
    """Load the JSONL dataset and validate the fields the scorer relies on."""
    dataset_path = Path(path).expanduser()
    if not dataset_path.is_file():
        raise DatasetError(f"dataset not found: {dataset_path}")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for number, line in enumerate(dataset_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetError(f"line {number} is not JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise DatasetError(f"line {number} is not an object")
        rows.append(row)
    if not rows:
        raise DatasetError(f"dataset is empty: {dataset_path}")
    for row in rows:
        identifier = str(row.get("id") or "")
        if not identifier:
            raise DatasetError("dataset row without id")
        if identifier in seen:
            raise DatasetError(f"duplicate id: {identifier}")
        seen.add(identifier)
        missing = [field for field in REQUIRED_FIELDS if field not in row]
        if missing:
            raise DatasetError(f"{identifier} is missing fields: {missing}")
        if row["answerability"] not in ANSWERABILITY:
            raise DatasetError(f"{identifier} has unknown answerability: {row['answerability']}")
        if row["dimension"] not in DIMENSIONS:
            raise DatasetError(f"{identifier} has unknown dimension: {row['dimension']}")
        if row["split"] not in SPLITS:
            raise DatasetError(f"{identifier} has unknown split: {row['split']}")
        if not isinstance(row["required_points"], list):
            raise DatasetError(f"{identifier} required_points must be a list")
        if not isinstance(row["scs_doc_ids"], list):
            raise DatasetError(f"{identifier} scs_doc_ids must be a list")
    return rows


def select_rows(
    rows: Iterable[dict[str, Any]],
    *,
    split: str | None = None,
    dimension: str | None = None,
    persona: str | None = None,
    answerability: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Filter the dataset deterministically, preserving id order."""
    selected = list(rows)
    for field, value in (
        ("split", split),
        ("dimension", dimension),
        ("persona", persona),
        ("answerability", answerability),
    ):
        if value:
            selected = [row for row in selected if row.get(field) == value]
    if limit is not None:
        selected = selected[: max(0, limit)]
    return selected
