#!/usr/bin/env python3
"""Score one answers dump under v1, each v2 correction and the full v2 protocol.

Usage:
    PYTHONPATH=src python scripts/audit_protocol_v2.py \
        --answers runs/P14-SENS-197/answers.jsonl \
        --out runs/P14-SENS-197
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scs_fkb.eval_accept.dataset import load_dataset  # noqa: E402
from scs_fkb.eval_accept.docmap import load_docmap  # noqa: E402
from scs_fkb.eval_accept.points import ConceptSource, PointOverrides  # noqa: E402
from scs_fkb.eval_accept.scoring import (  # noqa: E402
    ScoringConfig,
    aggregate,
    gate_result,
    score_row,
)


def _load_config(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _thresholds(config: dict) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    for name, spec in (config.get("thresholds") or {}).items():
        bound = spec.get("max", spec.get("min")) if isinstance(spec, dict) else spec
        if bound is not None:
            thresholds[name] = float(bound)
    return thresholds


def _variants(base: ScoringConfig) -> list[tuple[str, ScoringConfig]]:
    def clone(**changes) -> ScoringConfig:
        data = {
            "thresholds": dict(base.thresholds),
            "point_threshold_full": base.point_threshold_full,
            "point_threshold_partial": base.point_threshold_partial,
            "location_min_overlap": base.location_min_overlap,
            "max_terms": base.max_terms,
            "protocol": "v1",
            "point_partial_terms": base.point_partial_terms,
            "point_partial_min": base.point_partial_min,
            "location_mode": "label",
            "point_partial": 0.0,
            "basis_mode": "all_anchors",
            "basis_scope": "all",
        }
        data.update(changes)
        return ScoringConfig(**data)

    return [
        ("v1 (label, all anchors, all rows)", clone()),
        ("location only", clone(location_mode="document")),
        ("location + partial points", clone(location_mode="document", point_partial=0.5)),
        ("basis only", clone(basis_mode="any_anchor", basis_scope="answered")),
        (
            "v2 (all three)",
            clone(
                location_mode="document",
                point_partial=0.5,
                basis_mode="any_anchor",
                basis_scope="answered",
            ),
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", required=True)
    parser.add_argument(
        "--dataset-dir",
        default=str(Path(os.environ.get("SCS_FKB_DATA_ROOT", "")) / "eval" / "acceptance"),
    )
    parser.add_argument("--config", default=str(ROOT / "configs" / "eval-accept.yaml"))
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    data_dir = Path(args.dataset_dir).expanduser()
    rows = load_dataset(data_dir / "dataset.jsonl")
    docmap = load_docmap(data_dir / "doc-map.yaml")
    concepts = ConceptSource.load(ROOT / "configs" / "terms.yaml", data_dir / "domain-terms.yaml")
    overrides = PointOverrides.load(data_dir / "point-overrides.yaml")
    config = _load_config(Path(args.config))
    base = ScoringConfig(thresholds=_thresholds(config))

    answers: dict[str, dict] = {}
    for line in Path(args.answers).expanduser().read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            answers[str(record["id"])] = record
    missing = [row["id"] for row in rows if str(row["id"]) not in answers]
    if missing:
        raise SystemExit(f"missing answers for {len(missing)} rows: {missing[:5]}")

    lines = [
        "# Protocol v2 sensitivity (same 512 answers)",
        "",
        "| Variant | Coverage | Citation | Basis | Misanswer | Channel | As-of | Gate |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    results = {}
    for label, scoring in _variants(base):
        scored = []
        for row in rows:
            record = answers[str(row["id"])]
            result = {
                "answer": record.get("answer") or "",
                "citations": record.get("citations") or [],
                "abstained": bool(record.get("abstained")),
                "reason": record.get("reason") or "",
                "mode": record.get("mode") or "",
                "latency_ms": int(record.get("latency_ms") or 0),
            }
            scored.append(
                score_row(
                    row,
                    result,
                    docmap=docmap,
                    concepts=concepts,
                    overrides=overrides,
                    config=scoring,
                )
            )
        overall = aggregate(scored)
        gate = gate_result(overall, scoring.thresholds)
        results[label] = {"overall": overall, "gate": gate}
        lines.append(
            (
                "| {label} | {coverage:.4f} | {citation:.4f} | {basis:.4f} | "
                "{mis:.4f} | {channel:.4f} | {asof:.4f} | {gate} |"
            ).format(
                label=label,
                coverage=overall.get("point_coverage") or 0.0,
                citation=overall.get("citation_accuracy") or 0.0,
                basis=overall.get("basis_accuracy") or 0.0,
                mis=overall.get("misanswer_rate") or 0.0,
                channel=overall.get("refusal_channel_rate") or 0.0,
                asof=overall.get("asof_declaration_rate") or 0.0,
                gate="pass" if gate.get("passed") else "fail",
            )
        )
    lines += [
        "",
        "Each row is the same 512-answer dump scored with one scoring switch changed.",
        "The pass lines are unchanged (0.80 / 0.90 / 0.85 / 0.10).",
    ]
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        out = Path(args.out).expanduser()
        out.mkdir(parents=True, exist_ok=True)
        (out / "sensitivity.md").write_text(text, encoding="utf-8")
        (out / "sensitivity.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
