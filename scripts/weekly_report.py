#!/usr/bin/env python3
"""One read-only weekly report: currency, watch, candidates, knowledge and gaps.

Everything is read from the repository configuration and the local data root; the
only write is the dated markdown file under the run root.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import yaml

from scs_fkb.candidates import CandidateError, check_candidates, load_candidates
from scs_fkb.config import REPO_ROOT
from scs_fkb.facts import DEFAULT_FACTS_DIR, check_facts
from scs_fkb.gaps import collect_gaps
from scs_fkb.knowledge_v2 import check_playbooks
from scs_fkb.registry import RegistryError, check_currency, load_registry
from scs_fkb.watch import WatchError, due_report, run_watch

DEFAULT_REGISTRY = REPO_ROOT / "configs" / "corpus.yaml"
DEFAULT_WATCH = REPO_ROOT / "configs" / "source-watch.yaml"
DEFAULT_CANDIDATES = REPO_ROOT / "configs" / "candidates.yaml"
DEFAULT_TERMS = REPO_ROOT / "configs" / "terms.yaml"
DEFAULT_PLAYBOOKS = REPO_ROOT / "configs" / "playbooks"


def _section_errors(name: str, exc: Exception) -> str:
    return f"- {name}: error: {exc}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--task-id", default="P17-LOOP-209")
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--watch", default=str(DEFAULT_WATCH))
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    parser.add_argument("--terms", default=str(DEFAULT_TERMS))
    parser.add_argument("--playbooks", default=str(DEFAULT_PLAYBOOKS))
    parser.add_argument("--facts", default=str(DEFAULT_FACTS_DIR))
    args = parser.parse_args(argv)
    if not args.run_root:
        print("error: set SCS_FKB_RUN_ROOT or pass --run-root", file=sys.stderr)
        return 2

    today = date.fromisoformat(args.today)
    lines = [f"# Weekly knowledge checks — {args.today}", ""]
    lines.append(f"- Task: `{args.task_id}`")
    lines.append(f"- Data root: `{args.data_root or 'unset'}`")
    lines.append("- This run is read-only: no download, ingest, register edit or index rebuild.")
    lines.append("")

    try:
        registry = load_registry(Path(args.registry))
    except RegistryError as exc:
        print(f"registry error: {exc}", file=sys.stderr)
        return 1
    tier_counts: dict[str, int] = {}
    for entry in registry.values():
        if entry.get("lifecycle") != "active":
            continue
        tier = str(entry.get("authority_tier") or "?")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    active = sum(tier_counts.values())
    lines.append("## Registry")
    lines.append("")
    lines.append(f"- Sources: {len(registry)}; active: {active}")
    lines.append(
        "- Active tiers: "
        + ", ".join(f"{key} {value}" for key, value in sorted(tier_counts.items()))
    )
    lines.append("")

    lines.append("## Currency")
    lines.append("")
    try:
        currency = check_currency(registry, today=today, grace_days=30)
        lines.append(f"- Overdue: {len(currency['overdue'])}; errors: {len(currency['errors'])}")
        for row in currency["overdue"]:
            lines.append(f"- overdue `{row['id']}` {row['review_due']} ({row['days_overdue']}d)")
        for error in currency["errors"]:
            lines.append(f"- error: {error}")
    except RegistryError as exc:
        lines.append(_section_errors("currency", exc))
    try:
        due = due_report(Path(args.registry), today=today)["corpus"]
        lines.append(f"- Review dates reached: {len(due)}")
        for row in due:
            lines.append(f"- due `{row['id']}` {row['review_due']}")
    except RegistryError as exc:
        lines.append(_section_errors("due report", exc))
    lines.append("")

    lines.append("## Watch")
    lines.append("")
    try:
        reports = sorted(
            Path(args.run_root).expanduser().glob("*/watch-*.json"),
            key=lambda path: path.stat().st_mtime,
        )
        if reports:
            watch = json.loads(reports[-1].read_text(encoding="utf-8"))
            lines.append(f"- Source: latest live report `{reports[-1]}`")
        else:
            watch = run_watch(Path(args.watch), offline=True)
            lines.append("- Source: offline replay of the recorded statuses")
        lines.append(f"- Entries: {len(watch['results'])}; summary: {watch['summary']}")
        for result in watch["results"]:
            if result["status"] != "ok":
                lines.append(f"- `{result['id']}` {result['status']} {result['url']}")
    except (WatchError, OSError, json.JSONDecodeError) as exc:
        lines.append(_section_errors("watch", exc))
    lines.append("")

    lines.append("## Candidates")
    lines.append("")
    try:
        candidates = load_candidates(Path(args.candidates))
        summary = check_candidates(Path(args.candidates), today=today, registry_ids=set(registry))
        lines.append(f"- Candidates: {len(candidates)}; counts: {summary['counts']}")
        lines.append(f"- Due: {len(summary['due'])}; expired: {len(summary['expired'])}")
        for error in summary["errors"]:
            lines.append(f"- error: {error}")
    except CandidateError as exc:
        lines.append(_section_errors("candidates", exc))
    lines.append("")

    lines.append("## Knowledge")
    lines.append("")
    try:
        terms = yaml.safe_load(Path(args.terms).read_text(encoding="utf-8")) or {}
        counts: dict[str, int] = {}
        for term in terms.get("terms") or []:
            status = str(term.get("status") or "?")
            counts[status] = counts.get(status, 0) + 1
        lines.append(f"- Terms: {sum(counts.values())}; {counts}")
    except (OSError, yaml.YAMLError) as exc:
        lines.append(_section_errors("terms", exc))
    try:
        playbooks = check_playbooks(Path(args.playbooks))
        lines.append(
            f"- Playbooks: {playbooks.playbooks}; approved: {playbooks.approved}; "
            f"steps: {playbooks.steps}; errors: {len(playbooks.errors)}"
        )
        for error in playbooks.errors[:5]:
            lines.append(f"- error: {error}")
    except Exception as exc:  # noqa: BLE001 - the weekly report must still be written
        lines.append(_section_errors("playbooks", exc))
    if args.data_root:
        try:
            facts = check_facts(
                Path(args.facts),
                data_root=Path(args.data_root),
                registry_path=Path(args.registry),
                today=today,
            )
            lines.append(
                f"- Facts: errors {len(facts['errors'])}; expired {len(facts['expired'])}; "
                f"due {len(facts['due'])}"
            )
            for error in facts["errors"][:5]:
                lines.append(f"- error: {error}")
        except Exception as exc:  # noqa: BLE001 - facts need the processed store
            lines.append(_section_errors("facts", exc))
    else:
        lines.append("- Facts: skipped (data root unset)")
    lines.append("")

    lines.append("## Index")
    lines.append("")
    manifest_path = (
        Path(args.data_root) / "v2" / "index" / "manifest.json" if args.data_root else None
    )
    if manifest_path and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        lines.append(
            f"- index `{manifest.get('index_version')}`; documents {manifest.get('documents')}; "
            f"chunks {manifest.get('chunks')}; model `{manifest.get('model')}`"
        )
    else:
        lines.append("- Manifest not found")
    lines.append("")

    lines.append("## Gaps")
    lines.append("")
    gaps = collect_gaps(args.run_root)
    lines.append(
        f"- Feedback: {gaps['feedback']['total']} rows; unhelpful: {gaps['feedback']['unhelpful']}"
    )
    lines.append(
        f"- Logged queries: {gaps['queries']['total']}; abstained: {gaps['queries']['abstained']}"
    )
    if gaps["reasons"]:
        lines.append(
            "- Reasons: " + ", ".join(f"{key} {value}" for key, value in gaps["reasons"].items())
        )
    for row in gaps["top_questions"]:
        lines.append(f"- repeated: {row['question']} ({row['count']})")
    kb = gaps.get("kb") or {}
    lines.append(
        f"- Knowledge-station feedback: {kb.get('total', 0)} votes; "
        f"unhelpful: {kb.get('unhelpful', 0)}"
    )
    for row in kb.get("top_items") or []:
        lines.append(f"- unhelpful item: {row['item_id']} ({row['count']})")
    if not gaps["queries"]["total"]:
        lines.append("- Query log is off by default; set `SCS_FKB_LOG_QUERIES=on` to populate it.")
    lines.append("")

    lines.append("## Next actions")
    lines.append("")
    lines.append("- Review non-ok watch rows; changed pages may become candidates.")
    lines.append("- Review open candidates before expiry; admission follows docs/operations.md.")
    lines.append("- Promote repeated gap questions into sources, playbooks or FAQ drafts.")

    report_dir = Path(args.run_root).expanduser() / args.task_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"weekly-{args.today}.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"weekly report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
