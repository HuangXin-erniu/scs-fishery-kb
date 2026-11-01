from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import Chunk


class StoreError(RuntimeError):
    """Raised when processed data is missing or malformed."""


def processed_dir(data_root: Path) -> Path:
    return data_root / "processed"


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise StoreError(f"file not found: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise StoreError(f"file not found: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise StoreError(f"expected a JSON object: {path}")
    return value


def load_manifest(data_root: Path) -> dict[str, Any]:
    return read_json(processed_dir(data_root) / "manifest.json")


def load_chunks(data_root: Path) -> tuple[list[Chunk], dict[str, Any]]:
    directory = processed_dir(data_root)
    manifest = load_manifest(data_root)
    rows = read_jsonl(directory / "chunks.jsonl")
    chunks = [Chunk(**row) for row in rows]
    return chunks, manifest


def chunk_records(chunks: Iterable[Chunk]) -> list[dict[str, Any]]:
    return [asdict(chunk) for chunk in chunks]
