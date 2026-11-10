from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

CACHE_DIR = Path("web-cache")
INDEX_NAME = "index.json"
DEFAULT_CACHE_ENTRIES = 200
LABEL = "网络检索 · 未入知识库"


@dataclass(frozen=True)
class WebEvidence:
    evidence_id: str
    url: str
    canonical_url: str
    title: str
    publisher: str
    domain: str
    authority_tier: str
    source_class: str
    fetched_at: str
    content_hash: str
    snippet: str
    text_path: str
    search_query: str
    rank: int
    ttl_days: int
    status: str = "fetched"
    promotion_candidate_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def label(self) -> str:
        return LABEL


def cache_root(data_root: Path | str) -> Path:
    return Path(data_root).expanduser().resolve() / CACHE_DIR


def evidence_id(url: str, content_hash: str) -> str:
    digest = hashlib.sha256(f"{url}|{content_hash}".encode()).hexdigest()
    return f"WEBV-{digest[:12]}"


def _index_path(root: Path) -> Path:
    return root / INDEX_NAME


def load_index(data_root: Path | str) -> dict[str, dict[str, Any]]:
    path = _index_path(cache_root(data_root))
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_index(data_root: Path | str, index: dict[str, dict[str, Any]]) -> None:
    path = _index_path(cache_root(data_root))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    os.replace(temporary, path)


def _prune(data_root: Path | str, index: dict[str, dict[str, Any]], limit: int) -> None:
    if len(index) <= limit:
        return
    ordered = sorted(
        index.items(),
        key=lambda item: str(item[1].get("fetched_at") or ""),
        reverse=True,
    )
    keep = dict(ordered[:limit])
    for dropped in set(index) - set(keep):
        text_path = cache_root(data_root) / f"{dropped}.txt"
        try:
            text_path.unlink()
        except OSError:
            pass
    index.clear()
    index.update(keep)


def save_evidence(
    data_root: Path | str,
    evidence: WebEvidence,
    text: str,
    *,
    cache_entries: int = DEFAULT_CACHE_ENTRIES,
) -> WebEvidence:
    root = cache_root(data_root)
    root.mkdir(parents=True, exist_ok=True)
    text_path = root / f"{evidence.evidence_id}.txt"
    text_path.write_text(text, encoding="utf-8")
    stored = replace(
        evidence,
        text_path=str(text_path.relative_to(Path(data_root).expanduser().resolve())),
    )
    index = load_index(data_root)
    index[stored.evidence_id] = stored.to_dict()
    _prune(data_root, index, cache_entries)
    _write_index(data_root, index)
    return stored


def get_fresh(
    data_root: Path | str,
    url: str,
    *,
    now: datetime | None = None,
) -> WebEvidence | None:
    current = now or datetime.now(UTC)
    for row in load_index(data_root).values():
        if url not in {str(row.get("url")), str(row.get("canonical_url"))}:
            continue
        try:
            evidence = WebEvidence(**row)
        except TypeError:
            continue
        if is_fresh(evidence, current):
            return evidence
    return None


def is_fresh(evidence: WebEvidence, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    try:
        fetched = datetime.fromisoformat(evidence.fetched_at)
    except ValueError:
        return False
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=UTC)
    return current < fetched + timedelta(days=evidence.ttl_days)


def citation(evidence: WebEvidence) -> str:
    digest = evidence.content_hash[:8]
    fetched = evidence.fetched_at[:10]
    return f"[WEB:{evidence.domain}:{digest}] {evidence.url} (抓取于 {fetched})"


def promotion_draft(evidence: WebEvidence, *, today: date | None = None) -> dict[str, Any]:
    current = today or date.today()
    return {
        "id": "CAND-PENDING",
        "title": evidence.title or evidence.url,
        "url": evidence.url,
        "publisher": evidence.publisher,
        "proposed_tier": evidence.authority_tier,
        "proposed_class": "reference",
        "reason": "new",
        "first_seen": current.isoformat(),
        "expires_at": (current + timedelta(days=180)).isoformat(),
        "status": "open",
        "note": f"promoted from {evidence.evidence_id}; content {evidence.content_hash[:12]}",
    }


def label_for_answer() -> str:
    return LABEL


__all__ = [
    "CACHE_DIR",
    "DEFAULT_CACHE_ENTRIES",
    "LABEL",
    "WebEvidence",
    "cache_root",
    "citation",
    "evidence_id",
    "get_fresh",
    "is_fresh",
    "label_for_answer",
    "load_index",
    "promotion_draft",
    "save_evidence",
]
