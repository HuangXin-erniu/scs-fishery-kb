#!/usr/bin/env python3
"""Score the signed 30-item expert worksheet against the acceptance lines."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

THRESHOLDS = {"citation": 0.95, "conclusion": 0.85, "refusal": 0.90}
TRUTHY = {"1", "yes", "y", "true", "ok", "pass", "对", "通过"}


def _rate(rows: list[dict], column: str) -> tuple[int, int]:
    values = [str(row.get(column) or "").strip().lower() for row in rows]
    judged = [value for value in values if value]
    passed = sum(1 for value in judged if value in TRUTHY)
    return passed, len(judged)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worksheet", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--signature", default="")
    args = parser.parse_args(argv)
    rows = list(csv.DictReader(Path(args.worksheet).open(encoding="utf-8-sig")))
    signature_path = Path(args.signature) if args.signature else Path(args.worksheet).with_name(
        "expert-30-signature.json"
    )
    signature = {}
    if signature_path.is_file():
        signature = json.loads(signature_path.read_text(encoding="utf-8"))
    signed = bool(signature.get("name") and signature.get("date") and signature.get("affiliation"))
    result = {"n": len(rows), "signed": signed, "signature": signature, "dimensions": {}}
    failed: list[str] = []
    for name, column in (
        ("citation", "citation_ok"),
        ("conclusion", "conclusion_ok"),
        ("refusal", "refusal_ok"),
        ("asof", "asof_ok"),
    ):
        passed, judged = _rate(rows, column)
        rate = round(passed / judged, 4) if judged else None
        threshold = THRESHOLDS.get(name)
        ok = rate is not None and threshold is not None and rate >= threshold
        result["dimensions"][name] = {
            "passed": passed,
            "judged": judged,
            "rate": rate,
            "threshold": threshold,
            "ok": ok,
        }
        if threshold is not None and not ok:
            failed.append(name)
    result["pass"] = signed and not failed
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "expert-30-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# 30 题专家盲评结果",
        "",
        f"- 样本数：{len(rows)}",
        f"- 签字：{'已签' if signed else '未签（不得作为验收签字）'}",
        "- 签字人："
        f"{signature.get('name', '')} / {signature.get('affiliation', '')} / "
        f"{signature.get('date', '')}",
        "",
        "| 维度 | 通过/可判 | 通过率 | 线 | 结果 |",
        "|---|---:|---:|---:|---|",
    ]
    for name, row in result["dimensions"].items():
        rate = "n/a" if row["rate"] is None else f"{row['rate']:.4f}"
        threshold = "n/a" if row["threshold"] is None else f"{row['threshold']:.2f}"
        lines.append(
            f"| {name} | {row['passed']}/{row['judged']} | {rate} | {threshold} | "
            f"{'PASS' if row['ok'] else 'FAIL/n/a'} |"
        )
    lines += ["", f"结论：**{'PASS' if result['pass'] else '未通过或未签字'}**", ""]
    (out / "expert-30-result.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
