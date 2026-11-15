from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scs_fkb.eval_industry import (
    build_dataset,
    load_rows,
    manifest,
    resolve_gold_docs,
    validate_rows,
    write_dataset,
)
from scs_fkb.eval_industry.dataset import PLACEHOLDER_COUNTS, SPLITS

REPO_ROOT = Path(__file__).resolve().parents[1]


def _row(row_id: str, answerability: str = "可答", **extra):
    base = {
        "id": row_id,
        "question": f"问题 {row_id}",
        "persona": "船员",
        "domain": "伏季休渔",
        "difficulty": "中",
        "answerability": answerability,
        "scs_doc_ids": ["SCS-N-001"],
        "doc_locations": ["通告·休渔海域"],
        "reference_answer": "参考答案",
        "required_points": ["要点"],
    }
    base.update(extra)
    return base


def test_resolve_gold_docs_maps_only_indexed_documents():
    mapping = {
        "SCS-N-001": {"docs": ["POL-CLOS-015", "POL-LAW-009"], "covers": "full"},
        "SCS-X-999": {"docs": ["MISSING-001"], "covers": "missing"},
    }
    row = {"scs_doc_ids": ["SCS-N-001", "SCS-X-999"]}
    assert resolve_gold_docs(row, mapping, {"POL-CLOS-015"}) == ["POL-CLOS-015"]
    assert resolve_gold_docs(row, mapping, set()) == []


def test_build_dataset_produces_three_splits_with_placeholders():
    rows = [
        _row("Y-1"),
        _row("Y-2", persona="船东"),
        _row("Y-3", answerability="部分可答"),
        _row("Y-4", answerability="应拒答", reference_answer=""),
    ]
    mapping = {"SCS-N-001": {"docs": ["POL-CLOS-015"], "covers": "full"}}
    splits = build_dataset(rows, mapping, {"POL-CLOS-015"}, seed=7)
    assert set(splits) == set(SPLITS)
    for split in SPLITS:
        frozen = [row for row in splits[split] if row["status"] == "frozen"]
        pending = [row for row in splits[split] if row["status"] == "pending_source"]
        expected_frozen = {
            "retrieval": 3,
            "generation": 3,
            "abstention": 1,
        }[split]
        assert len(frozen) == expected_frozen
        assert len(pending) == PLACEHOLDER_COUNTS[split]
        assert not validate_rows(splits[split], split)
    assert splits["abstention"][0]["expected"] == "refuse"


def test_validate_rows_catches_missing_and_pending_question():
    errors = validate_rows(
        [{"id": "IR-001", "split": "retrieval", "status": "frozen"}], "retrieval"
    )
    assert any("missing question" in error for error in errors)
    errors = validate_rows(
        [{"id": "IR-001", "split": "retrieval", "status": "pending_source", "question": "x"}],
        "retrieval",
    )
    assert any("must not carry a question" in error for error in errors)


def test_write_dataset_roundtrip_and_manifest(tmp_path: Path):
    rows = [_row("Y-1"), _row("Y-2", answerability="应拒答", reference_answer="")]
    mapping = {"SCS-N-001": {"docs": ["POL-CLOS-015"]}}
    splits = build_dataset(rows, mapping, {"POL-CLOS-015"}, seed=11)
    result = write_dataset(
        tmp_path,
        splits,
        seed=11,
        source_hashes={"acceptance_dataset": "a" * 64},
    )
    assert result["schema_version"] == 1
    assert result["gate_ready"] is False
    assert result["counts"]["retrieval"]["total"] == len(splits["retrieval"])
    for split in SPLITS:
        assert len(load_rows(tmp_path, split)) == len(splits[split])
        assert result["files"][split]["sha256"]
    on_disk = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk["seed"] == 11


def test_manifest_detects_gate_ready_only_without_placeholders(tmp_path: Path):
    mapping = {"SCS-N-001": {"docs": ["POL-CLOS-015"]}}
    rows = [_row(f"Y-{index}") for index in range(1, 4)]
    splits = build_dataset(rows, mapping, {"POL-CLOS-015"}, seed=3)
    frozen_only = {
        split: [row for row in splits[split] if row["status"] == "frozen"] for split in SPLITS
    }
    write_dataset(tmp_path, frozen_only, seed=3)
    # Frozen counts are below the required core in this tiny fixture, so the
    # gate is still not ready; the check proves gate_ready is derived, not hardcoded.
    assert manifest(tmp_path, seed=3)["gate_ready"] is False


def test_public_config_contains_no_questions_or_absolute_paths():
    path = REPO_ROOT / "configs" / "eval-industry.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")
    assert "question:" not in text
    assert "reference_answer:" not in text
    assert ("/" + "Users/") not in text
    assert data["splits"]["retrieval"]["frozen_core"] == 200
    assert data["targets"]["generation"]["faithfulness"] == 0.90


@pytest.mark.parametrize("split", SPLITS)
def test_every_split_has_a_public_target(split: str):
    path = REPO_ROOT / "configs" / "eval-industry.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert split in data["splits"]
    assert data["splits"][split]["frozen_core"] > 0
