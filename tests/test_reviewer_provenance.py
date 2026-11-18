from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import score_expert_sample  # noqa: E402
import validate_human_review  # noqa: E402
from review_provenance import check_human, reviewer_kind  # noqa: E402

WORKSHEET_FIELDS = [
    "sample_no",
    "id",
    "citation_ok",
    "conclusion_ok",
    "refusal_ok",
    "asof_ok",
]


def _write_worksheet(path: Path, rows: int, verdict: str = "pass") -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*WORKSHEET_FIELDS, "human_verdict"])
        writer.writeheader()
        value = "1" if verdict == "pass" else "0"
        for index in range(rows):
            writer.writerow(
                {
                    "sample_no": index + 1,
                    "id": f"Y-{index:03d}",
                    "citation_ok": value,
                    "conclusion_ok": value,
                    "refusal_ok": value,
                    "asof_ok": value,
                    "human_verdict": verdict,
                }
            )


def _signature(**overrides: str) -> dict:
    base = {
        "name": "测试专家",
        "affiliation": "测试单位",
        "date": "2026-11-18",
        "reviewer_type": "human",
        "attestation": "本人独立完成 30 题盲评，未参考项目方的检测器标记、预判或旧复核记录。",
    }
    base.update(overrides)
    return base


def test_reviewer_kind() -> None:
    assert reviewer_kind({"reviewer_type": "human"}) == "human"
    assert reviewer_kind({"reviewer_type": "ai_assistant"}) == "non_human"
    assert reviewer_kind({"reviewer_type": "robot"}) == "unknown"
    assert reviewer_kind({}) == "missing"


def test_check_human_requires_human_and_attestation() -> None:
    assert check_human({"reviewer_type": "human"})[0] is True
    assert check_human({"reviewer_type": "ai_assistant"})[0] is False
    assert check_human({"reviewer_type": "human"}, require_attestation=True)[0] is False
    assert (
        check_human(
            {"reviewer_type": "human", "attestation": "本人独立完成"}, require_attestation=True
        )[0]
        is True
    )


def test_expert_scorer_accepts_human_signature(tmp_path: Path) -> None:
    worksheet = tmp_path / "expert-30-worksheet.csv"
    signature = tmp_path / "expert-30-signature.json"
    _write_worksheet(worksheet, 30)
    signature.write_text(json.dumps(_signature(), ensure_ascii=False), encoding="utf-8")

    code = score_expert_sample.main(
        ["--worksheet", str(worksheet), "--out-dir", str(tmp_path), "--signature", str(signature)]
    )
    result = json.loads((tmp_path / "expert-30-result.json").read_text(encoding="utf-8"))
    assert code == 0
    assert result["signed"] is True
    assert result["signature_kind"] == "human"
    assert result["pass"] is True


def test_expert_scorer_rejects_ai_signature(tmp_path: Path) -> None:
    worksheet = tmp_path / "expert-30-worksheet.csv"
    signature = tmp_path / "expert-30-signature.json"
    _write_worksheet(worksheet, 30)
    signature.write_text(
        json.dumps(_signature(reviewer_type="ai_assistant"), ensure_ascii=False), encoding="utf-8"
    )

    score_expert_sample.main(
        ["--worksheet", str(worksheet), "--out-dir", str(tmp_path), "--signature", str(signature)]
    )
    result = json.loads((tmp_path / "expert-30-result.json").read_text(encoding="utf-8"))
    assert result["signed"] is False
    assert result["signature_kind"] == "non_human"
    assert result["pass"] is False


def test_expert_scorer_rejects_ai_worksheet_even_with_human_signature(tmp_path: Path) -> None:
    worksheet = tmp_path / "expert-30-worksheet.csv"
    signature = tmp_path / "expert-30-signature.json"
    _write_worksheet(worksheet, 30)
    # add an explicit AI provenance column to the worksheet itself
    rows = list(csv.DictReader(worksheet.open(encoding="utf-8-sig")))
    with worksheet.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*rows[0].keys(), "reviewer_type"])
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "reviewer_type": "ai_assistant"})
    signature.write_text(json.dumps(_signature(), ensure_ascii=False), encoding="utf-8")

    score_expert_sample.main(
        ["--worksheet", str(worksheet), "--out-dir", str(tmp_path), "--signature", str(signature)]
    )
    result = json.loads((tmp_path / "expert-30-result.json").read_text(encoding="utf-8"))
    assert result["signed"] is False
    assert result["worksheet_human"] is False
    assert result["pass"] is False


def test_expert_scorer_requires_attestation(tmp_path: Path) -> None:
    worksheet = tmp_path / "expert-30-worksheet.csv"
    signature = tmp_path / "expert-30-signature.json"
    _write_worksheet(worksheet, 30)
    signature.write_text(
        json.dumps(_signature(attestation=""), ensure_ascii=False), encoding="utf-8"
    )

    score_expert_sample.main(
        ["--worksheet", str(worksheet), "--out-dir", str(tmp_path), "--signature", str(signature)]
    )
    result = json.loads((tmp_path / "expert-30-result.json").read_text(encoding="utf-8"))
    assert result["signed"] is False
    assert result["pass"] is False


def _run_validator(tmp_path: Path, provenance: dict | None, extra: list[str] | None = None) -> dict:
    worksheet = tmp_path / "human.csv"
    _write_worksheet(worksheet, 100)
    if provenance is not None:
        (tmp_path / "review-provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False), encoding="utf-8"
        )
    out = tmp_path / "gate.json"
    code = validate_human_review.main(["--csv", str(worksheet), "--out", str(out), *(extra or [])])
    result = json.loads(out.read_text(encoding="utf-8"))
    result["_code"] = code
    return result


def test_validator_accepts_human_provenance(tmp_path: Path) -> None:
    result = _run_validator(tmp_path, {"reviewer_type": "human"})
    assert result["human_review_valid"] is True
    assert result["pass"] is True
    assert result["_code"] == 0


def test_validator_rejects_ai_provenance(tmp_path: Path) -> None:
    result = _run_validator(tmp_path, {"reviewer_type": "ai_assistant"})
    assert result["human_review_valid"] is False
    assert result["pass"] is False
    assert result["_code"] == 2


def test_validator_rejects_missing_provenance(tmp_path: Path) -> None:
    result = _run_validator(tmp_path, None)
    assert result["human_review_valid"] is False
    assert result["pass"] is False
    assert result["_code"] == 2


def test_validator_allows_explicit_legacy_escape_hatch(tmp_path: Path) -> None:
    result = _run_validator(tmp_path, None, ["--allow-unverified"])
    assert result["human_review_valid"] is True
    assert result["pass"] is True
    assert result["_code"] == 0
