#!/usr/bin/env python3
"""Draw a fresh 30-question expert sample from the frozen audit answers.

The expert sees only the question, the delivered answer and its citations.  The
detector flags, the prior review verdicts and the 150-row audit sample are
excluded.  The pack and the answer key are hashed before the expert opens them.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

QUOTAS = {"休渔": 6, "证照": 6, "执法": 6, "生态": 5, "预报": 4, "补贴": 2, "其他": 1}


def _rows(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _excluded(paths: list[Path]) -> set[str]:
    ids: set[str] = set()
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("id"):
                ids.add(str(row["id"]))
    return ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20261117)
    args = parser.parse_args(argv)
    records = _rows(Path(args.answers))
    excluded = _excluded([Path(path) for path in args.exclude])
    pool = [row for row in records if str(row.get("id")) not in excluded]
    rng = random.Random(args.seed)
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in pool:
        buckets[str(row.get("theme") or "其他")].append(row)
    selected: list[dict] = []
    seen: set[str] = set()
    for theme, quota in QUOTAS.items():
        rows = buckets.get(theme, [])
        rng.shuffle(rows)
        for row in rows:
            if len(selected) >= args.n:
                break
            if str(row["id"]) in seen:
                continue
            selected.append(row)
            seen.add(str(row["id"]))
            if sum(1 for item in selected if str(item.get("theme")) == theme) >= quota:
                break
    remaining = [row for row in pool if str(row["id"]) not in seen]
    rng.shuffle(remaining)
    for row in remaining:
        if len(selected) >= args.n:
            break
        selected.append(row)
        seen.add(str(row["id"]))
    selected.sort(key=lambda row: str(row["id"]))

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "expert-30-questions.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample_no", "id", "theme", "question"])
        for index, row in enumerate(selected, start=1):
            writer.writerow([index, row["id"], row.get("theme", ""), row.get("question", "")])

    lines = [
        "# 专家盲评包（30 题）",
        "",
        "> 评分只看问题、答案与引用；不要参考任何检测器标记、旧复核记录或我方预判。",
        "",
    ]
    for index, row in enumerate(selected, start=1):
        cites = ", ".join(
            f"{item.get('doc_id')} §{item.get('section', '')}"
            for item in (row.get("citations") or [])
        )
        lines += [
            f"## {index}. {row.get('question', '')}",
            "",
            f"- id: `{row['id']}`",
            f"- theme: {row.get('theme', '')}",
            f"- citations: {cites or '（无）'}",
            "",
            row.get("visible_answer", ""),
            "",
            "---",
            "",
        ]
    pack = "\n".join(lines)
    (out / "expert-30-answer-pack.md").write_text(pack, encoding="utf-8")

    with (out / "expert-30-worksheet.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "sample_no",
                "id",
                "citation_ok",
                "conclusion_ok",
                "refusal_ok",
                "asof_ok",
                "note",
            ]
        )
        for index, row in enumerate(selected, start=1):
            writer.writerow([index, row["id"], "", "", "", "", ""])

    key = {
        "seed": args.seed,
        "n": len(selected),
        "ids": [row["id"] for row in selected],
        "questions": {row["id"]: row.get("question", "") for row in selected},
        "references": {row["id"]: row.get("reference", "") for row in selected},
    }
    (out / "expert-30-key.json").write_text(
        json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    seal = {
        "pack_sha256": hashlib.sha256(pack.encode("utf-8")).hexdigest(),
        "key_sha256": hashlib.sha256(
            (out / "expert-30-key.json").read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest(),
        "seed": args.seed,
        "excluded": sorted(excluded),
    }
    (out / "seal.json").write_text(json.dumps(seal, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"selected={len(selected)} excluded={len(excluded)} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
