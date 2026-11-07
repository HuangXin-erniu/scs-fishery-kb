from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

CSV_FIELDS = (
    "id",
    "split",
    "domain",
    "persona",
    "sea_area",
    "answerability",
    "dimension",
    "abstained",
    "mode",
    "reason",
    "latency_ms",
    "citation_docs",
    "citation_sections",
    "citation_location_source",
    "citation_hit",
    "citation_accuracy",
    "point_coverage",
    "points_hit",
    "points_judgeable",
    "misanswer",
    "correct_refusal",
    "asof_declared",
    "basis_score",
    "band",
    "flags",
    "error",
)


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (list, tuple)):
        return ";".join(str(item) for item in value)
    return str(value)


def write_rows_csv(scored: list[dict[str, Any]], path: Path) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in scored:
        writer.writerow({key: _fmt(row.get(key)) for key in CSV_FIELDS})
    path.write_text(buffer.getvalue(), encoding="utf-8")


def metrics_payload(
    *,
    dataset_manifest: dict[str, Any],
    docmap_summary: dict[str, Any],
    overall: dict[str, Any],
    groups: dict[str, dict[str, Any]],
    gate: dict[str, Any],
    clusters: list[dict[str, Any]],
    latency: dict[str, Any],
    arm: str,
    rows: int,
    environment: dict[str, Any],
) -> dict[str, Any]:
    return {
        "instrument": {
            "name": "acceptance",
            "questions": rows,
            "dataset": dataset_manifest,
            "docmap": docmap_summary,
        },
        "arm": arm,
        "environment": environment,
        "overall": overall,
        "groups": groups,
        "gate": gate,
        "reason_clusters": clusters,
        "latency": latency,
    }


def _table(rows: list[dict[str, Any]]) -> str:
    header = (
        "| 组 | 题数 | 要点覆盖 | 引用准确 | 误答率 | 拒答渠道 | 时效声明 | 口径正确 | 时延均值 |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )

    def cell(value: Any) -> str:
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value)

    body = "".join(
        "| {name} | {questions} | {point_coverage} | {citation_accuracy} | "
        "{misanswer_rate} | {refusal_channel_rate} | {asof_declaration_rate} | "
        "{basis_accuracy} | {latency} |\n".format(
            name=item.get("name"),
            questions=item.get("questions", ""),
            point_coverage=cell(item.get("point_coverage")),
            citation_accuracy=cell(item.get("citation_accuracy")),
            misanswer_rate=cell(item.get("misanswer_rate")),
            refusal_channel_rate=cell(item.get("refusal_channel_rate")),
            asof_declaration_rate=cell(item.get("asof_declaration_rate")),
            basis_accuracy=cell(item.get("basis_accuracy")),
            latency=cell(item.get("latency_mean_ms")),
        )
        for item in rows
    )
    return header + body


def _group_rows(name: str, buckets: dict[str, dict[str, Any]]) -> str:
    rows = [{"name": key, **value} for key, value in buckets.items()]
    if not rows:
        return f"### {name}\n\nNo rows.\n"
    return f"### {name}\n\n{_table(rows)}"


def write_report(
    *,
    path: Path,
    arm: str,
    rows: int,
    overall: dict[str, Any],
    groups: dict[str, dict[str, Any]],
    gate: dict[str, Any],
    clusters: list[dict[str, Any]],
    latency: dict[str, Any],
    failures: list[dict[str, Any]],
) -> None:
    lines = [
        "# Acceptance baseline report",
        "",
        f"- Arm: `{arm}`",
        f"- Questions: {rows}",
        f"- Answered: {overall.get('answered')} ({overall.get('answer_rate')})",
        f"- Gate passed: {gate['passed']}",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Rows | Pass line | Passed |",
        "|---|---:|---:|---:|---|",
    ]
    checks = gate.get("checks") or {}
    rows_map = {
        "misanswer_rate": "refusal_rows",
        "citation_accuracy": "citation_rows",
        "point_coverage": "point_rows",
        "refusal_channel_rate": "refusal_rows",
        "asof_declaration_rate": "asof_rows",
        "basis_accuracy": "basis_rows",
    }
    for name, check in checks.items():
        value = overall.get(name)
        lines.append(
            f"| {name} | {value if value is not None else '—'} | "
            f"{overall.get(rows_map.get(name, ''), '')} | "
            f"{check.get('threshold')} | {check.get('passed')} |"
        )
    if gate.get("failures"):
        lines += ["", "Gate failures:", ""]
        lines += [f"- {item}" for item in gate["failures"]]
    lines += [
        "",
        f"- Point coverage rows: {overall.get('point_rows')} "
        f"({overall.get('judgeable_points')} judgeable points; "
        f"{overall.get('rows_with_unjudgeable_points')} rows carry review-needed points)",
        f"- Citation rows: {overall.get('citation_rows')}; citation coverage: "
        f"{overall.get('citation_coverage')}",
        f"- Location match sources: {overall.get('location_sources')}",
        f"- Refusal rows: {overall.get('refusal_rows')}; as-of rows: {overall.get('asof_rows')}; "
        f"basis rows: {overall.get('basis_rows')}",
        f"- Band mean: {overall.get('band_mean')} over {overall.get('band_rows')} rows",
        f"- Latency: mean {latency.get('mean')} ms, median {latency.get('median')} ms, "
        f"P95 {latency.get('p95')} ms",
        "",
        "## Groups",
        "",
    ]
    for name, buckets in groups.items():
        lines.append(_group_rows(name, buckets))
        lines.append("")
    lines += ["## Reason clusters", "", "| Kind | Name | Count |", "|---|---|---:|"]
    lines += [f"| {item['kind']} | {item['name']} | {item['count']} |" for item in clusters]
    lines += ["", "## Representative failures", ""]
    if not failures:
        lines.append("None.")
    for item in failures:
        lines.append(
            f"- {item['id']}: band={item.get('band')}, points={item.get('point_coverage')}, "
            f"citation={item.get('citation_accuracy')}, reason={item.get('reason')}, "
            f"flags={','.join(item.get('flags') or [])}"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_metrics(payload: dict[str, Any], path: Path) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
