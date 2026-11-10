#!/usr/bin/env python3
"""Live smoke test for the optional web-evidence layer on freshness questions.

The run is read-only for the knowledge base: it writes web cache entries under
the local data root and a report under the run root. It never edits the corpus,
never promotes a candidate and never ingests a page.

Usage:
    python scripts/eval_web_v2.py --data-root DIR --run-root DIR [--delay 5]
"""

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
from scs_fkb.web_v2 import citation, load_allowlist, search_web
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


def _provider(settings: dict[str, object]):
    from scs_fkb.web_v2 import build_provider

    searxng = os.environ.get("SEARXNG_URL", "").strip() or str(settings.get("searxng_url") or "")
    return build_provider(
        searxng,
        fallback=str(settings.get("fallback") or "ddgs"),
        timeout=float(settings.get("timeout_seconds") or 10),
        backend=str(settings.get("backend") or "auto"),
        engines=str(settings.get("engines") or ""),
    )


def _markdown(rows: list[dict], totals: dict) -> str:
    lines = [
        "# Web-evidence smoke",
        "",
        f"- Queries: {totals['queries']}",
        f"- With at least one evidence: {totals['with_evidence']}",
        f"- Evidence records: {totals['evidences']}",
        f"- Non-allowlisted results dropped: {totals['dropped']}",
        f"- Fetch failures: {totals['failures']}",
        f"- Cache hits: {totals['cached']}",
        f"- Distinct domains: {totals['domains']}",
        "- Writes: web cache under the data root; no corpus edit, no ingest.",
        "",
        "| # | Query | Nature | Trigger | Evidences | Domains | Dropped | Failures |",
        "|---|---|---|---|---:|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {n} | {question} | {nature} | {reason} | {evidences} | {domains} | "
            "{dropped} | {failures} |".format(**row)
        )
    lines.extend(["", "## Evidence", ""])
    for row in rows:
        for item in row["citations"]:
            lines.append(f"- Q{row['n']}: {item}")
        for failure in row["errors"]:
            lines.append(f"- Q{row['n']} failure: {failure}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--allowlist", default=str(REPO_ROOT / "configs" / "web-sources.yaml"))
    parser.add_argument("--searxng-url", default=os.environ.get("SEARXNG_URL", ""))
    parser.add_argument("--task-id", default="P17-WEB-207")
    parser.add_argument("--delay", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-evidences", type=int, default=2)
    args = parser.parse_args(argv)
    if not args.data_root or not args.run_root:
        print("error: set SCS_FKB_DATA_ROOT and SCS_FKB_RUN_ROOT", file=sys.stderr)
        return 2

    allowlist_path = Path(args.allowlist)
    allowlist = load_allowlist(allowlist_path)
    settings = provider_settings(yaml.safe_load(allowlist_path.read_text(encoding="utf-8")))
    if args.searxng_url:
        settings["searxng_url"] = args.searxng_url
    provider = _provider(settings)

    rows: list[dict] = []
    domain_counter: Counter[str] = Counter()
    for index, (question, nature) in enumerate(QUERIES, start=1):
        result = search_web(
            question,
            nature=nature,
            allowlist=allowlist,
            provider=provider,
            data_root=Path(args.data_root),
            mode="on",
            max_results=int(settings.get("max_results") or 5),
            max_evidences=args.max_evidences,
            site_hint=str(settings.get("site_hint") or ""),
            spacing_seconds=float(settings.get("spacing_seconds") or 2.0),
            max_bytes=int(settings.get("max_bytes") or 2_000_000),
            snippet_chars=int(settings.get("snippet_chars") or 300),
            cache_entries=int(settings.get("cache_entries") or 200),
            user_agent=str(settings.get("user_agent") or "scs-fkb-web/1.0"),
        )
        domains = sorted({item.domain for item in result.evidences})
        domain_counter.update(domains)
        errors = [str(item.get("error") or "") for item in result.failures]
        rows.append(
            {
                "n": index,
                "question": question,
                "nature": nature,
                "reason": result.reason,
                "triggered": result.triggered,
                "evidences": len(result.evidences),
                "domains": ", ".join(domains) or "—",
                "dropped": len(result.dropped),
                "failures": len(result.failures),
                "cached": result.cached,
                "citations": [citation(item) for item in result.evidences],
                "errors": errors,
            }
        )
        if args.delay and index < len(QUERIES):
            time.sleep(args.delay)

    totals = {
        "queries": len(rows),
        "with_evidence": sum(1 for row in rows if row["evidences"]),
        "evidences": sum(row["evidences"] for row in rows),
        "dropped": sum(row["dropped"] for row in rows),
        "failures": sum(row["failures"] for row in rows),
        "cached": sum(row["cached"] for row in rows),
        "domains": len(domain_counter),
    }
    report_dir = Path(args.run_root) / args.task_id
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "web-smoke.json").write_text(
        json.dumps({"totals": totals, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (report_dir / "web-smoke.md").write_text(_markdown(rows, totals), encoding="utf-8")
    print(json.dumps(totals, ensure_ascii=False, indent=2))
    print(f"report: {report_dir / 'web-smoke.md'}")
    return 0 if totals["evidences"] else 1


if __name__ == "__main__":
    sys.exit(main())
