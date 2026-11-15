"""Answer cache for the standard RAG arm.

Two layers: an exact key (question + persona + region/year + index version +
mode + prompt/config hashes) and an optional semantic layer (cosine similarity
of question embeddings).  A cached answer is invalidated when the index version
changes or the entry is older than its TTL.  Only validated, non-abstained
answers are cached.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_TTL_DAYS = 30
DEFAULT_THRESHOLD = 0.95
CACHE_DIR = "answer-cache"


def config_hash(**values: Any) -> str:
    payload = json.dumps(values, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def question_key(
    question: str,
    *,
    persona: str = "general",
    region: str | None = None,
    year: int | None = None,
    index_version: str = "",
    mode: str = "standard",
    prompt_version: str = "",
    config: str = "",
) -> str:
    normalized = " ".join(question.split()).lower()
    payload = "\n".join(
        [
            normalized,
            str(persona or "general"),
            str(region or ""),
            str(year or ""),
            str(index_version),
            str(mode),
            str(prompt_version),
            str(config),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


class AnswerCache:
    """JSONL-backed answer cache with optional semantic lookup."""

    def __init__(
        self,
        root: Path | str,
        *,
        encoder: Any = None,
        threshold: float = DEFAULT_THRESHOLD,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> None:
        self.root = Path(root).expanduser().resolve() / CACHE_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "entries.jsonl"
        self.encoder = encoder
        self.threshold = float(threshold)
        self.ttl_days = int(ttl_days)
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        entries: dict[str, dict[str, Any]] = {}
        if not self.path.is_file():
            return entries
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return entries
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = str(row.get("key") or "")
            if key:
                entries[key] = row
        return entries

    def _fresh(self, entry: dict[str, Any], *, index_version: str, now: datetime) -> bool:
        if index_version and str(entry.get("index_version") or "") != index_version:
            return False
        try:
            created = datetime.fromisoformat(str(entry.get("created_at") or ""))
        except ValueError:
            return False
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        return now - created <= timedelta(days=self.ttl_days)

    def _hit(self, entry: dict[str, Any], kind: str) -> dict[str, Any]:
        payload = dict(entry.get("payload") or {})
        payload["cache"] = {
            "hit": True,
            "type": kind,
            "created_at": str(entry.get("created_at") or ""),
        }
        return payload

    def get(
        self,
        key: str,
        *,
        question: str = "",
        index_version: str = "",
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        current = now or datetime.now(UTC)
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and self._fresh(entry, index_version=index_version, now=current):
                return self._hit(entry, "exact")
            candidates = list(self._entries.values())
        if not self.encoder or not question or not candidates:
            return None
        try:
            vector = [float(value) for value in self.encoder.embed_query(question)]
        except Exception:  # noqa: BLE001 - cache miss on encoder failure
            return None
        best: tuple[float, dict[str, Any]] | None = None
        for item in candidates:
            if not self._fresh(item, index_version=index_version, now=current):
                continue
            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                continue
            score = _cosine(vector, [float(value) for value in embedding])
            if score >= self.threshold and (best is None or score > best[0]):
                best = (score, item)
        if best is None:
            return None
        payload = self._hit(best[1], "semantic")
        payload["cache"]["similarity"] = round(best[0], 4)
        return payload

    def put(
        self,
        key: str,
        payload: dict[str, Any],
        *,
        question: str = "",
        index_version: str = "",
        embedding: list[float] | None = None,
    ) -> None:
        if embedding is None and self.encoder and question:
            try:
                embedding = [float(value) for value in self.encoder.embed_query(question)]
            except Exception:  # noqa: BLE001 - still store the exact entry
                embedding = None
        entry = {
            "key": key,
            "question": " ".join(question.split()),
            "index_version": str(index_version),
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "embedding": embedding,
            "payload": payload,
        }
        with self._lock:
            self._entries[key] = entry
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except OSError:
                pass

    @property
    def size(self) -> int:
        return len(self._entries)


__all__ = [
    "AnswerCache",
    "CACHE_DIR",
    "DEFAULT_TTL_DAYS",
    "DEFAULT_THRESHOLD",
    "config_hash",
    "question_key",
]
