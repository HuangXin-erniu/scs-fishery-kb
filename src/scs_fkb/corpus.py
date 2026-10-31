from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from .config import DEFAULT_CONFIG, ConfigError
from .models import Source


class CorpusError(RuntimeError):
    """Raised when the corpus register or a source file is invalid."""


def load_corpus(path: Path | None = None) -> dict[str, Any]:
    register_path = Path(path) if path else DEFAULT_CONFIG
    if not register_path.is_file():
        raise CorpusError(f"corpus register not found: {register_path}")
    data = yaml.safe_load(register_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CorpusError("corpus register must be a mapping")
    if data.get("schema_version") != 1:
        raise CorpusError("unsupported corpus schema_version")
    if not isinstance(data.get("sources"), list) or not data["sources"]:
        raise CorpusError("corpus register has no sources")
    return data


def acquired_sources(data: dict[str, Any]) -> list[Source]:
    sources: list[Source] = []
    for raw in data["sources"]:
        if not isinstance(raw, dict):
            raise CorpusError("source entry must be a mapping")
        if raw.get("status") != "acquired":
            continue
        sources.append(_source_from_mapping(raw))
    if not sources:
        raise CorpusError("no acquired sources in the corpus register")
    return sources


def _source_from_mapping(raw: dict[str, Any]) -> Source:
    required = (
        "id",
        "category",
        "title",
        "title_zh",
        "publisher",
        "type",
        "format",
        "location",
        "license",
        "sensitivity",
        "status",
        "hash",
    )
    missing = [key for key in required if key not in raw]
    if missing:
        raise CorpusError(f"source {raw.get('id', '?')} is missing fields: {missing}")
    for key in ("location", "hash"):
        if not raw.get(key):
            raise CorpusError(f"acquired source {raw['id']} has no {key}")
    return Source(
        id=str(raw["id"]),
        category=str(raw["category"]),
        title=str(raw["title"]),
        title_zh=str(raw["title_zh"]),
        publisher=str(raw["publisher"]),
        year=raw.get("year"),
        doc_type=str(raw["type"]),
        format=str(raw["format"]),
        location=str(raw["location"]),
        license=str(raw["license"]),
        sensitivity=str(raw["sensitivity"]),
        status=str(raw["status"]),
        hash=str(raw["hash"]),
    )


def resolve_source_file(source: Source, root: Path) -> tuple[Path, str]:
    location = Path(source.location)
    if location.is_absolute() or ".." in location.parts:
        raise CorpusError(f"source {source.id} location must stay under the data root")
    root = root.expanduser().resolve()
    path = (root / location).resolve()
    if not path.is_relative_to(root):
        raise CorpusError(f"source {source.id} location escapes the data root")
    if not path.is_file():
        raise CorpusError(f"source file not found: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if source.hash and digest != source.hash:
        raise CorpusError(f"source hash mismatch for {source.id}")
    return path, digest


def read_document_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CorpusError(f"cannot decode source file: {path}")


def config_error(message: str) -> ConfigError:
    return ConfigError(message)
