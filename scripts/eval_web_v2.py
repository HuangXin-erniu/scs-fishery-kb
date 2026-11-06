#!/usr/bin/env python3
"""Smoke-test the ephemeral web channel on 20 freshness questions."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

from scs_fkb.config import REPO_ROOT
from scs_fkb.web_v2 import build_provider, citation, load_allowlist, search_web
from scs_fkb.web_v2.policy import provider_settings

QUERIES = [
    ("2026年南海伏季休渔 农业农村部", "rule"),
    ("2026年海洋伏季休渔专项执法行动", "rule"),
    ("2026年南海区专项捕捞许可", "rule"),
    ("广东省2026年伏季休渔", "rule"),
    ("广西2026年海洋伏季休渔", "rule"),
    ("海南省2026年休渔", "rule"),
    ("福建省2026年海洋伏季休渔", "rule"),
    ("2026年渔船油价补贴 标准", "status"),
    ("渔业捕捞许可证 换发 2026", "rule"),
    ("渔捞日志 填报 规定", "rule"),
    ("渔业船舶检验 2026", "rule"),
    ("南海 台风 预警 2026", "warning"),
    ("农业农村部 渔业 通知 2026", "status"),
    ("南海区 海洋捕捞 产量 2025", "statistics"),
    ("渔业资源增殖保护费 2026", "rule"),
    ("渔港 管理 2026", "rule"),
    ("渔业行政处罚 2026", "rule"),
    ("海洋捕捞 渔具 最小网目 2026", "rule"),
    ("南海 开渔 2026", "status"),
    ("渔业船员 值班 规定", "rule"),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--allowlist", default=str(REPO_ROOT / "configs" / "web-sources.yaml"))
    parser.add_argument("--searxng-url", default=os.environ.get("SEARXNG_URL", ""))
    parser.add_argument("--delay", type=float, default=5.0)
    parser.add_argument("--report-dir", default="P10-WEB-140")
    args = parser.parse_args(argv)
    if not args.data_root or not args.run_root:
        print("error: set SCS_FKB_DATA_ROOT and SCS_FKB_RUN_ROOT", file=sys.stderr)
        return 2
    allowlist = load_allowlist(Path(args.allowlist))
    settings = provider_settings(yaml.safe_load(Path(args.allowlist).read_text(encoding="utf-8")))
    provider = build_provider(
        args.searxng_url or settings["searxng_url"],
        fallback=settings["fallback"],
        timeout=settings["timeout_seconds"],
        backend=settings["backend"],
    )
    rows = []
    for index, (question, nature) in enumerate(QUERIES, start=1):
        result = search_web(
            question,
            nature=nature,
            allowlist=allowlist,
            provider=provider,
            data_root=Path(args.data_root),
            max_results=3,
            explicit=True,
        )
        rows.append(
            {
                "n": index,
                "question": question,
                "nature": nature,
                "triggered": result.triggered,
                "provider": result.provider,
                "evidences": len(result.evidences),
                "cached": result.cached,
                "dropped": len(result.dropped),
                "failures": len(result.failures),
                "citations": [citation(item) for item in result.evidences],
                "ttls": [item.ttl_days for item in result.evidences],
                "failure_detail": result.failures[:2],
            }
        )
        print(
            f"{index:02d} evidence={len(result.evidences)} "
            f"dropped={len(result.dropped)} failures={len(result.failures)} {question}"
        )
        if index < len(QUERIES) and args.delay > 0:
            time.sleep(args.delay)
    report_path = Path(args.run_root).expanduser() / args.report_dir / "smoke.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    total = len(rows)
    with_evidence = sum(1 for row in rows if row["evidences"] > 0)
    total_evidence = sum(row["evidences"] for row in rows)
    total_dropped = sum(row["dropped"] for row in rows)
    total_failures = sum(row["failures"] for row in rows)
    lines = [
        f"# {args.report_dir} web smoke",
        "",
        f"- Queries: {total}",
        f"- Queries with at least one allowlisted evidence: {with_evidence}",
        f"- Evidence records: {total_evidence}",
        f"- Non-allowlisted drops: {total_dropped}",
        f"- Fetch/search failures: {total_failures}",
        f"- Providers: {dict(Counter(row['provider'] for row in rows))}",
        "",
        "| # | Question | Nature | Evidence | Dropped | Failures | TTLs |",
        "|---:|---|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['n']} | {row['question']} | {row['nature']} | {row['evidences']} | "
            f"{row['dropped']} | {row['failures']} | {row['ttls']} |"
        )
    lines += ["", "## Citation samples", ""]
    for row in rows:
        for item in row["citations"][:1]:
            lines.append(f"- `{row['question']}` → {item}")
    lines += ["", "## Failures", ""]
    failures = [(row["question"], detail) for row in rows for detail in row["failure_detail"]]
    lines += [f"- `{question}`: {detail}" for question, detail in failures] or ["- none"]
    lines += [
        "",
        "The full extracted text stays in the local web cache; this report contains "
        "metadata and citations only.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "queries": total,
        "with_evidence": with_evidence,
        "evidence": total_evidence,
        "dropped": total_dropped,
        "failures": total_failures,
        "report": str(report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
