from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..store import write_json

SNAPSHOT_SCHEMA = 1
SNAPSHOT_ROOT = Path("v2") / "snapshots"
MANIFEST_NAME = Path("v2") / "snapshots.json"


class SnapshotError(RuntimeError):
    """Raised when a source cannot be snapshotted safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_source(root: Path, source_id: str, location: str) -> Path:
    if not location:
        raise SnapshotError(f"{source_id}: location is empty")
    relative = Path(location)
    if relative.is_absolute() or ".." in relative.parts:
        raise SnapshotError(f"{source_id}: location must stay under the data root")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise SnapshotError(f"{source_id}: location escapes the data root")
    if path.is_symlink():
        raise SnapshotError(f"{source_id}: symlink sources are not accepted")
    if not path.exists():
        raise SnapshotError(f"{source_id}: source path does not exist")
    return path


def _relative_snapshot(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _file_entries(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        if item.is_symlink():
            raise SnapshotError(f"symlink in source tree: {item.name}")
        entries.append(
            {
                "path": item.relative_to(path).as_posix(),
                "bytes": item.stat().st_size,
                "sha256": sha256_file(item),
            }
        )
    if not entries:
        raise SnapshotError(f"source directory is empty: {path.name}")
    return entries


def _tree_hash(entries: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        [{"path": item["path"], "sha256": item["sha256"]} for item in entries],
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_tree(source: Path, target: Path) -> None:
    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue
        if item.is_symlink():
            raise SnapshotError(f"symlink in source tree: {item.name}")
        _copy_file(item, target / item.relative_to(source))


def _existing_metadata(snapshot_dir: Path) -> dict[str, Any] | None:
    path = snapshot_dir / "snapshot.json"
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _snapshot_file(
    source_id: str,
    root: Path,
    path: Path,
    source_hash: str,
    snapshot_root: Path,
    *,
    source_format: str,
) -> dict[str, Any]:
    digest = sha256_file(path)
    if source_hash and digest != source_hash:
        raise SnapshotError(f"{source_id}: source.hash_mismatch")
    target = snapshot_root / source_hash / "source" / path.name
    metadata_path = snapshot_root / source_hash / "snapshot.json"
    if target.is_file() and metadata_path.is_file():
        metadata = _existing_metadata(snapshot_root / source_hash)
        if metadata and metadata.get("sha256") == digest:
            return metadata
    if (snapshot_root / source_hash).exists():
        shutil.rmtree(snapshot_root / source_hash)
    _copy_file(path, target)
    metadata = {
        "source_id": source_id,
        "kind": "file",
        "source_hash": source_hash,
        "sha256": digest,
        "bytes": path.stat().st_size,
        "mime": mimetypes.guess_type(path.name)[0] or source_format,
        "snapshot_path": _relative_snapshot(root, target),
        "files": [{"path": path.name, "bytes": path.stat().st_size, "sha256": digest}],
        "verified": True,
    }
    write_json(snapshot_root / source_hash / "snapshot.json", metadata)
    return metadata


def _snapshot_directory(
    source_id: str,
    root: Path,
    path: Path,
    source_hash: str,
    snapshot_root: Path,
    *,
    source_format: str,
) -> dict[str, Any]:
    entries = _file_entries(path)
    tree_digest = _tree_hash(entries)
    target_root = snapshot_root / source_hash
    metadata_path = target_root / "snapshot.json"
    if metadata_path.is_file():
        metadata = _existing_metadata(target_root)
        if metadata and metadata.get("tree_sha256") == tree_digest:
            return metadata
    if target_root.exists():
        shutil.rmtree(target_root)
    _copy_tree(path, target_root / "files")
    metadata = {
        "source_id": source_id,
        "kind": "directory",
        "source_hash": source_hash,
        "tree_sha256": tree_digest,
        "bytes": sum(item["bytes"] for item in entries),
        "mime": "inode/directory",
        "snapshot_path": _relative_snapshot(root, target_root / "files"),
        "files": entries,
        "verified": False,
        "verification": "directory manifest; register hash is an edition manifest, not a tree hash",
        "source_format": source_format,
    }
    write_json(target_root / "snapshot.json", metadata)
    return metadata


def snapshot_registry(
    registry: dict[str, dict[str, Any]],
    data_root: Path | str,
) -> dict[str, Any]:
    """Snapshot every acquired source and write ``v2/snapshots.json``.

    Single-file sources are hash-verified against the register. Directory
    sources (yearbook editions) get a file manifest and a tree hash; the register
    hash is recorded but not treated as a tree hash. A missing, escaping or
    symlinked source is an error; a partial snapshot is replaced atomically.
    """
    root = Path(data_root).expanduser().resolve()
    snapshot_root = root / SNAPSHOT_ROOT
    sources: dict[str, Any] = {}
    errors: list[str] = []
    for source_id, source in sorted(registry.items()):
        if source.get("status") != "acquired":
            continue
        location = str(source.get("location") or "")
        source_hash = str(source.get("hash") or "")
        source_format = str(source.get("format") or "")
        try:
            path = _resolve_source(root, source_id, location)
            if path.is_dir():
                metadata = _snapshot_directory(
                    source_id, root, path, source_hash, snapshot_root, source_format=source_format
                )
            else:
                metadata = _snapshot_file(
                    source_id, root, path, source_hash, snapshot_root, source_format=source_format
                )
        except SnapshotError as exc:
            errors.append(str(exc))
            continue
        sources[source_id] = metadata

    if errors:
        raise SnapshotError("; ".join(errors))

    manifest_sources = {
        source_id: {
            "kind": metadata["kind"],
            "source_hash": metadata["source_hash"],
            "snapshot_path": metadata["snapshot_path"],
            "bytes": metadata["bytes"],
            "files": len(metadata["files"]),
            "verified": metadata["verified"],
        }
        for source_id, metadata in sources.items()
    }
    digest = hashlib.sha256(
        json.dumps(manifest_sources, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": SNAPSHOT_SCHEMA,
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "snapshot_manifest_sha256": digest,
        "sources": sources,
        "summary": {
            "sources": len(sources),
            "files": sum(len(item["files"]) for item in sources.values()),
            "bytes": sum(item["bytes"] for item in sources.values()),
            "verified": sum(1 for item in sources.values() if item["verified"]),
            "unverified": sum(1 for item in sources.values() if not item["verified"]),
        },
    }
    write_json(root / MANIFEST_NAME, manifest)
    return manifest


__all__ = ["MANIFEST_NAME", "SNAPSHOT_SCHEMA", "SnapshotError", "sha256_file", "snapshot_registry"]
