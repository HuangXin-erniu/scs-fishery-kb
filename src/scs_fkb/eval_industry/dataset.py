"""Build and validate the Track B industry-standard evaluation dataset.

Design notes
------------
* Track B is separate from the frozen 512-question acceptance instrument
  (Track A).  It is built from the same private rows plus a set of placeholder
  rows that Phase 3 fills from the new practical sources.
* Only the private dataset lives outside the repository.  The public tree gets
  the schema, metric definitions and this loader, never questions or answers.
* Sampling is deterministic: a seed and a stable grouping key are recorded in
  ``manifest.json`` so another maintainer can reproduce the exact id set.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SPLITS = ("retrieval", "generation", "abstention")

# Frozen core counts: the number of real rows each split must contain before
# the dataset can be used as a gate.  Placeholders are excluded from the core.
FROZEN_CORE = {"retrieval": 200, "generation": 120, "abstention": 70}
PLACEHOLDER_COUNTS = {"retrieval": 100, "generation": 80, "abstention": 30}
ANSWERABLE = {"可答", "部分可答"}
REFUSAL = "应拒答"

REQUIRED_COMMON = ("id", "split", "status")
REQUIRED_FROZEN = {
    "retrieval": ("question", "persona", "domain", "answerability", "difficulty", "gold_docs"),
    "generation": (
        "question",
        "persona",
        "domain",
        "answerability",
        "difficulty",
        "reference_answer",
        "gold_docs",
    ),
    "abstention": ("question", "persona", "domain", "expected"),
}


def sha256_file(path: Path | str) -> str:
    """Return the SHA-256 hash of a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_rows(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def resolve_gold_docs(
    row: dict[str, Any],
    mapping: dict[str, dict[str, Any]],
    indexed_docs: set[str],
) -> list[str]:
    """Map the instrument's ``SCS-*`` ids to indexed repository documents."""
    docs: set[str] = set()
    for scs_id in row.get("scs_doc_ids") or []:
        entry = mapping.get(str(scs_id)) or {}
        for doc_id in entry.get("docs") or []:
            if doc_id in indexed_docs:
                docs.add(str(doc_id))
    return sorted(docs)


def _grouped(
    rows: list[dict[str, Any]], keys: tuple[str, ...]
) -> dict[tuple[str, ...], list[dict]]:
    groups: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row.get(key) or "") for key in keys)].append(row)
    return groups


def stratified_pick(
    rows: list[dict[str, Any]],
    count: int,
    seed: int,
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Deterministically pick ``count`` rows, spread across the grouping keys."""
    groups = _grouped(rows, keys)
    for key in sorted(groups):
        random.Random(f"{seed}:{key}").shuffle(groups[key])
    picked: list[dict[str, Any]] = []
    cursor = 0
    ordered_keys = sorted(groups)
    while len(picked) < count and ordered_keys:
        progress = False
        for key in ordered_keys:
            bucket = groups[key]
            if cursor < len(bucket):
                picked.append(bucket[cursor])
                progress = True
                if len(picked) >= count:
                    break
        if not progress:
            break
        cursor += 1
    return picked


def _gold(row: dict[str, Any], docs: list[str]) -> list[dict[str, str | None]]:
    return [{"doc_id": doc_id, "section": None} for doc_id in docs]


def build_dataset(
    rows: list[dict[str, Any]],
    mapping: dict[str, dict[str, Any]],
    indexed_docs: set[str],
    *,
    seed: int = 20261113,
) -> dict[str, list[dict[str, Any]]]:
    """Build the three Track B splits from the private acceptance rows.

    ``rows`` is the 512-row instrument, ``mapping`` is the doc map and
    ``indexed_docs`` is the set of document ids in the current index.
    """
    answerable: list[dict[str, Any]] = []
    refusals: list[dict[str, Any]] = []
    for row in rows:
        answerability = str(row.get("answerability") or "")
        if answerability in ANSWERABLE:
            docs = resolve_gold_docs(row, mapping, indexed_docs)
            if docs:
                answerable.append({**row, "_gold_docs": docs})
        elif answerability == REFUSAL:
            refusals.append(row)

    retrieval_core = stratified_pick(
        answerable,
        FROZEN_CORE["retrieval"],
        seed,
        ("persona", "domain", "difficulty", "answerability"),
    )
    retrieval_ids = {str(row["id"]) for row in retrieval_core}

    generation_pool = [
        row
        for row in answerable
        if str(row["id"]) in retrieval_ids and str(row.get("reference_answer") or "").strip()
    ]
    generation_core = stratified_pick(
        generation_pool,
        FROZEN_CORE["generation"],
        seed + 1,
        ("persona", "domain", "difficulty", "answerability"),
    )
    abstention_core = stratified_pick(
        refusals,
        FROZEN_CORE["abstention"],
        seed + 2,
        ("persona", "domain", "difficulty"),
    )

    retrieval = [
        {
            "id": f"IR-{index:03d}",
            "split": "retrieval",
            "status": "frozen",
            "source_row_id": str(row["id"]),
            "question": str(row["question"]),
            "persona": row.get("persona"),
            "domain": row.get("domain"),
            "answerability": row.get("answerability"),
            "difficulty": row.get("difficulty"),
            "gold_docs": _gold(row, row["_gold_docs"]),
            "gold_locations": list(row.get("doc_locations") or []),
            "provenance": "acceptance-v5",
        }
        for index, row in enumerate(retrieval_core, start=1)
    ]
    generation = [
        {
            "id": f"IG-{index:03d}",
            "split": "generation",
            "status": "frozen",
            "source_row_id": str(row["id"]),
            "question": str(row["question"]),
            "persona": row.get("persona"),
            "domain": row.get("domain"),
            "answerability": row.get("answerability"),
            "difficulty": row.get("difficulty"),
            "reference_answer": str(row.get("reference_answer") or ""),
            "required_points": list(row.get("required_points") or []),
            "gold_docs": _gold(row, row["_gold_docs"]),
            "provenance": "acceptance-v5",
        }
        for index, row in enumerate(generation_core, start=1)
    ]
    abstention = [
        {
            "id": f"IA-{index:03d}",
            "split": "abstention",
            "status": "frozen",
            "source_row_id": str(row["id"]),
            "question": str(row["question"]),
            "persona": row.get("persona"),
            "domain": row.get("domain"),
            "difficulty": row.get("difficulty"),
            "expected": "refuse",
            "reason": str(row.get("notes") or row.get("intent") or ""),
            "provenance": "acceptance-v5",
        }
        for index, row in enumerate(abstention_core, start=1)
    ]

    for split, rows_for_split in (
        ("retrieval", retrieval),
        ("generation", generation),
        ("abstention", abstention),
    ):
        start = len(rows_for_split) + 1
        for offset in range(PLACEHOLDER_COUNTS[split]):
            rows_for_split.append(
                {
                    "id": f"{_prefix(split)}-{start + offset:03d}",
                    "split": split,
                    "status": "pending_source",
                    "question": None,
                    "persona": None,
                    "domain": None,
                    "note": "Filled in Phase 3 from the practical-source batches.",
                }
            )

    return {"retrieval": retrieval, "generation": generation, "abstention": abstention}


def _prefix(split: str) -> str:
    return {"retrieval": "IR", "generation": "IG", "abstention": "IA"}[split]


def validate_rows(rows: list[dict[str, Any]], split: str) -> list[str]:
    """Return a list of schema errors; empty means valid."""
    if split not in SPLITS:
        return [f"unknown split: {split}"]
    errors: list[str] = []
    seen: set[str] = set()
    for row in rows:
        row_id = str(row.get("id") or "<missing>")
        for field in REQUIRED_COMMON:
            if field not in row:
                errors.append(f"{row_id}: missing {field}")
        if row.get("split") != split:
            errors.append(f"{row_id}: split is {row.get('split')!r}, expected {split!r}")
        if row_id in seen:
            errors.append(f"{row_id}: duplicate id")
        seen.add(row_id)
        status = row.get("status")
        if status == "pending_source":
            if row.get("question") is not None:
                errors.append(f"{row_id}: pending row must not carry a question")
            continue
        if status != "frozen":
            errors.append(f"{row_id}: unknown status {status!r}")
            continue
        for field in REQUIRED_FROZEN[split]:
            if not row.get(field):
                errors.append(f"{row_id}: missing {field}")
        if split in ("retrieval", "generation"):
            if row.get("answerability") not in ANSWERABLE:
                errors.append(f"{row_id}: answerability must be one of {sorted(ANSWERABLE)}")
            gold = row.get("gold_docs") or []
            if not gold or any(not item.get("doc_id") for item in gold):
                errors.append(f"{row_id}: gold_docs must be a non-empty list of doc ids")
        if split == "abstention" and row.get("expected") != "refuse":
            errors.append(f"{row_id}: abstention rows must expect 'refuse'")
    return errors


def load_rows(dataset_dir: Path | str, split: str) -> list[dict[str, Any]]:
    """Load one split from ``<dataset_dir>/<split>.jsonl``."""
    path = Path(dataset_dir) / f"{split}.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"dataset split not found: {path}")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def manifest(
    dataset_dir: Path | str,
    *,
    seed: int,
    source_hashes: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe the dataset on disk: counts, hashes and freeze state."""
    directory = Path(dataset_dir)
    counts: dict[str, dict[str, int]] = {}
    files: dict[str, dict[str, Any]] = {}
    frozen = True
    for split in SPLITS:
        rows = load_rows(directory, split)
        frozen_count = sum(1 for row in rows if row.get("status") == "frozen")
        pending_count = sum(1 for row in rows if row.get("status") == "pending_source")
        counts[split] = {
            "total": len(rows),
            "frozen": frozen_count,
            "pending_source": pending_count,
            "required_core": FROZEN_CORE[split],
        }
        if frozen_count < FROZEN_CORE[split] or pending_count:
            frozen = False
        files[split] = {
            "path": f"{split}.jsonl",
            "sha256": sha256_file(directory / f"{split}.jsonl"),
            "rows_sha256": _sha256_rows(rows),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "counts": counts,
        "files": files,
        "source_hashes": source_hashes or {},
        "gate_ready": frozen,
        "note": (
            "Track B skeleton: the frozen core comes from the private 512 instrument; "
            "placeholder rows are filled from the practical-source batches in Phase 3. "
            "Not a merge gate until gate_ready is true."
        ),
        **(extra or {}),
    }


def write_dataset(
    dataset_dir: Path | str,
    splits: dict[str, list[dict[str, Any]]],
    *,
    seed: int,
    source_hashes: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate, write the three JSONL splits and the manifest."""
    directory = Path(dataset_dir)
    directory.mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        rows = splits[split]
        errors = validate_rows(rows, split)
        if errors:
            raise ValueError("; ".join(errors[:20]))
        payload = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
        (directory / f"{split}.jsonl").write_text(payload + "\n", encoding="utf-8")
    result = manifest(directory, seed=seed, source_hashes=source_hashes, extra=extra)
    (directory / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result
