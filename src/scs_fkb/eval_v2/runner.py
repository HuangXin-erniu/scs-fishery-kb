from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .metrics import aggregate, gate_ok, score_row

THRESHOLDS = {
    "answer_correctness": 0.85,
    "citation_resolution": 0.99,
    "context_recall": 0.80,
    "abstention_accuracy": 0.90,
}


def load_questions(path: Path | str = "configs/eval-v2.yaml") -> list[dict[str, Any]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    questions = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(questions, list) or not questions:
        raise ValueError(f"eval questions are empty: {path}")
    return questions


def run_eval(
    service: Any,
    *,
    questions_path: Path | str = "configs/eval-v2.yaml",
    split: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    questions = load_questions(questions_path)
    if split:
        questions = [item for item in questions if item.get("split") == split]
    if limit:
        questions = questions[:limit]
    rows: list[dict[str, Any]] = []
    for item in questions:
        expected = item.get("expected") or {}
        try:
            result = service.query(str(item["question"]), web="off")
            citations = [
                citation.model_dump() if hasattr(citation, "model_dump") else dict(citation)
                for citation in getattr(result, "citations", []) or []
            ]
            row = {
                "id": item.get("id"),
                "question": item.get("question"),
                "split": item.get("split"),
                "review_status": item.get("review_status"),
                "expected": expected,
                "answer": str(getattr(result, "answer", "")),
                "abstained": bool(getattr(result, "abstained", False)),
                "reason": str(getattr(result, "reason", "")),
                "mode": str(getattr(result, "mode", "")),
                "citations": citations,
                "latency_ms": int(getattr(result, "latency_ms", 0) or 0),
                "error": "",
            }
        except Exception as exc:  # noqa: BLE001 - per-question failure is data
            row = {
                "id": item.get("id"),
                "question": item.get("question"),
                "split": item.get("split"),
                "review_status": item.get("review_status"),
                "expected": expected,
                "answer": "",
                "abstained": True,
                "reason": "runner_error",
                "mode": "abstain",
                "citations": [],
                "latency_ms": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }
        row.update(score_row(row))
        rows.append(row)

    groups: dict[str, dict[str, Any]] = {}
    for group_name, group_rows in {
        "overall": rows,
        "dev": [row for row in rows if row.get("split") == "dev"],
        "test": [row for row in rows if row.get("split") == "test"],
        "reviewed": [row for row in rows if row.get("review_status") == "reviewed"],
        "draft": [row for row in rows if row.get("review_status") == "draft"],
    }.items():
        if group_rows:
            groups[group_name] = aggregate(group_rows)
    passed, failures = gate_ok(
        groups.get("dev", {}),
        {
            "answer_correctness": THRESHOLDS["answer_correctness"],
            "citation_resolution": THRESHOLDS["citation_resolution"],
            "context_recall": THRESHOLDS["context_recall"],
        },
    )
    abstention = groups.get("overall", {}).get("abstention_accuracy")
    if abstention is None or abstention < THRESHOLDS["abstention_accuracy"]:
        passed = False
        failures.append(f"abstention_accuracy={abstention} < {THRESHOLDS['abstention_accuracy']}")
    return {
        "questions": len(rows),
        "groups": groups,
        "thresholds": THRESHOLDS,
        "passed": passed,
        "failures": failures,
        "rows": rows,
    }


def write_report(result: dict[str, Any], run_root: Path | str) -> tuple[Path, Path]:
    import json

    directory = Path(run_root).expanduser() / "P10-EVAL-145"
    directory.mkdir(parents=True, exist_ok=True)
    metrics_path = directory / "metrics.json"
    metrics_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# P10-EVAL-145 evaluation report",
        "",
        f"- Questions: {result['questions']}",
        f"- Gate passed: {result['passed']}",
        f"- Failures: {', '.join(result['failures']) or 'none'}",
        "",
        "| Group | Questions | Correctness | Faithfulness | Citation | "
        "Context recall | Abstention |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, group in result["groups"].items():
        lines.append(
            f"| {name} | {group['questions']} | {group.get('answer_correctness', 0):.4f} | "
            f"{group.get('faithfulness', 0):.4f} | {group.get('citation_resolution', 0):.4f} | "
            f"{group.get('context_recall', 0):.4f} | {group.get('abstention_accuracy')} |"
        )
    lines += ["", "## Failures", ""]
    failures = [
        row
        for row in result["rows"]
        if row.get("error")
        or (row.get("expected") or {}).get("abstained") != row.get("abstained")
        or (
            not (row.get("expected") or {}).get("abstained")
            and row.get("answer_correctness", 0) < 0.5
        )
    ]
    lines += [
        f"- {row['id']}: correctness={row.get('answer_correctness')}, "
        f"abstained={row.get('abstained')}, reason={row.get('reason')}"
        for row in failures[:40]
    ] or ["- none"]
    lines += [
        "",
        "Draft provision questions are not gold; test metrics are report-only.",
        "Metrics are deterministic proxies, not an LLM judge.",
        "",
    ]
    report_path = directory / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return metrics_path, report_path


__all__ = ["THRESHOLDS", "load_questions", "run_eval", "write_report"]
