from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

COVERS = ("full", "partial", "missing", "out_of_scope")


class DocMapError(ValueError):
    """Raised when the private document map is missing or malformed."""


@dataclass(frozen=True)
class DocMapEntry:
    scs_id: str
    docs: tuple[str, ...]
    covers: str
    title: str = ""
    registry_status: str = ""
    note: str = ""


@dataclass
class DocMap:
    """Two-way map between instrument document ids and repository document ids."""

    entries: dict[str, DocMapEntry] = field(default_factory=dict)
    _reverse: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> DocMap:
        entries: dict[str, DocMapEntry] = {}
        for scs_id, value in mapping.items():
            if not isinstance(scs_id, str) or not scs_id.startswith("SCS-"):
                raise DocMapError(f"invalid instrument document id: {scs_id!r}")
            if not isinstance(value, dict):
                raise DocMapError(f"{scs_id} entry must be an object")
            docs = value.get("docs") or []
            if not isinstance(docs, list) or any(not isinstance(item, str) for item in docs):
                raise DocMapError(f"{scs_id} docs must be a list of strings")
            covers = str(value.get("covers") or "")
            if covers not in COVERS:
                raise DocMapError(f"{scs_id} covers must be one of {COVERS}")
            if covers in ("missing", "out_of_scope") and docs:
                raise DocMapError(f"{scs_id} is {covers} but names documents")
            if covers in ("full", "partial") and not docs:
                raise DocMapError(f"{scs_id} is {covers} but names no document")
            entries[scs_id] = DocMapEntry(
                scs_id=scs_id,
                docs=tuple(doc.strip() for doc in docs if doc.strip()),
                covers=covers,
                title=str(value.get("title") or ""),
                registry_status=str(value.get("registry_status") or ""),
                note=str(value.get("note") or ""),
            )
        reverse: dict[str, list[str]] = {}
        for entry in entries.values():
            for doc_id in entry.docs:
                reverse.setdefault(doc_id, []).append(entry.scs_id)
        return cls(
            entries=entries,
            _reverse={doc_id: tuple(sorted(ids)) for doc_id, ids in reverse.items()},
        )

    def entry(self, scs_id: str) -> DocMapEntry | None:
        return self.entries.get(scs_id)

    def docs_for(self, scs_id: str) -> tuple[str, ...]:
        found = self.entries.get(scs_id)
        return found.docs if found else ()

    def scs_for_doc(self, doc_id: str) -> tuple[str, ...]:
        return self._reverse.get(doc_id, ())

    def covers(self, scs_id: str) -> str:
        found = self.entries.get(scs_id)
        return found.covers if found else "unknown"

    def expected_ids(self, row: dict[str, Any]) -> list[str]:
        return [str(item) for item in row.get("scs_doc_ids") or [] if str(item).startswith("SCS-")]

    def unresolved(self, rows: Iterable[dict[str, Any]]) -> list[str]:
        referenced: set[str] = set()
        for row in rows:
            referenced.update(self.expected_ids(row))
        return sorted(item for item in referenced if item not in self.entries)

    def summary(self) -> dict[str, Any]:
        counts = dict.fromkeys(COVERS, 0)
        for entry in self.entries.values():
            counts[entry.covers] += 1
        counts["total"] = len(self.entries)
        return counts


def load_docmap(path: Path | str) -> DocMap:
    """Load the YAML document map written next to the private dataset."""
    import yaml

    map_path = Path(path).expanduser()
    if not map_path.is_file():
        raise DocMapError(f"document map not found: {map_path}")
    data = yaml.safe_load(map_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise DocMapError(f"document map is not an object: {map_path}")
    mapping = data.get("mapping")
    if not isinstance(mapping, dict) or not mapping:
        raise DocMapError(f"document map has no mapping: {map_path}")
    return DocMap.from_mapping(mapping)
