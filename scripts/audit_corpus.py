#!/usr/bin/env python3
"""Five corpus-health checks that answer-side scans cannot see."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scs_fkb.audit.normalize import ngrams  # noqa: E402
from scs_fkb.registry import load_registry  # noqa: E402

NAV = ("网站地图", "主办", "技术支持", "微信", "打印本页", "首页 >", "政务公开")
OCR_BAD = ("□", "�", "??")


def _chunks(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            out.setdefault(str(row["doc_id"]), "")
            out[str(row["doc_id"])] += str(row.get("text", "")) + "\n"
    return out


def _write(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", "data"))
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    registry = load_registry()
    chunks = _chunks(Path(args.data_root) / "v2" / "processed" / "chunks.jsonl")
    title_rows, level_rows, currency_rows, version_rows, quality_rows = [], [], [], [], []
    for doc_id, entry in registry.items():
        if doc_id not in chunks:
            continue
        title = str(entry.get("title", ""))
        body = chunks.get(doc_id, "")
        first = re.sub(r"\s+", "", body[:3000])
        title_grams = ngrams(title, 2)
        coverage = len(title_grams & ngrams(first, 2)) / max(1, len(title_grams))
        if coverage < 0.60:
            title_rows.append(
                {
                    "doc_id": doc_id,
                    "title": title,
                    "similarity": f"{coverage:.2f}",
                    "first_chars": first[:80],
                }
            )
        publisher = str(entry.get("publisher", ""))
        level = str(entry.get("level", ""))
        if ("省" in publisher or "市" in publisher) and level == "national":
            level_rows.append(
                {
                    "doc_id": doc_id,
                    "publisher": publisher,
                    "level": level,
                    "reason": "publisher has province/city but level=national",
                }
            )
        if any(word in body[:2000] for word in ("工作动态", "政务公开", "领导活动")):
            level_rows.append(
                {
                    "doc_id": doc_id,
                    "publisher": publisher,
                    "level": level,
                    "reason": "body looks like government work news",
                }
            )
        effective = entry.get("effective") or {}
        if not effective.get("from"):
            currency_rows.append(
                {"doc_id": doc_id, "title": title, "issue": "effective.from empty"}
            )
        if any(word in body[:2000] for word in ("拟废止", "征求意见")):
            currency_rows.append(
                {"doc_id": doc_id, "title": title, "issue": "draft/repeal marker in body"}
            )
        if ("名录" in title or "标准" in title or "GB/T" in title) and not entry.get("year"):
            version_rows.append(
                {"doc_id": doc_id, "title": title, "issue": "list/standard without year"}
            )
        noise = sum(body.count(marker) for marker in NAV) / max(1, len(body))
        broken = sum(body.count(marker) for marker in OCR_BAD) / max(1, len(body))
        if noise > 0.001 or broken > 0.001:
            quality_rows.append(
                {"doc_id": doc_id, "noise_ratio": f"{noise:.4f}", "ocr_bad_ratio": f"{broken:.4f}"}
            )
    _write(out / "corpus-title.csv", ["doc_id", "title", "similarity", "first_chars"], title_rows)
    _write(out / "corpus-level.csv", ["doc_id", "publisher", "level", "reason"], level_rows)
    _write(out / "corpus-currency.csv", ["doc_id", "title", "issue"], currency_rows)
    _write(out / "corpus-version.csv", ["doc_id", "title", "issue"], version_rows)
    _write(out / "corpus-quality.csv", ["doc_id", "noise_ratio", "ocr_bad_ratio"], quality_rows)
    print(
        f"docs={len([d for d in registry if d in chunks])} title={len(title_rows)} "
        f"level={len(level_rows)} currency={len(currency_rows)} "
        f"version={len(version_rows)} quality={len(quality_rows)}"
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
