#!/usr/bin/env python3
"""Run 512 service audit in hard-timeout batches, then concatenate."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--batch-timeout", type=int, default=240)
    parser.add_argument("--total", type=int, default=512)
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir)
    batch_dir = out_dir / "batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.setdefault("LLM_TIMEOUT", "10")
    failures = []
    for offset in range(0, args.total, args.batch_size):
        target = batch_dir / f"batch-{offset:04d}.jsonl"
        if target.exists() and target.stat().st_size > 0:
            print(f"skip {offset}", flush=True)
            continue
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "build_audit_artifact.py"),
            "--mode",
            "service",
            "--offset",
            str(offset),
            "--limit",
            str(args.batch_size),
            "--timeout",
            "20",
            "--out",
            str(target),
        ]
        print(f"batch {offset}", flush=True)
        try:
            subprocess.run(cmd, cwd=ROOT, env=env, timeout=args.batch_timeout, check=False)
        except subprocess.TimeoutExpired:
            print(f"timeout batch {offset}", flush=True)
            failures.append(offset)
            if target.exists():
                target.unlink()
    merged = out_dir / "audit-answers-512-service.jsonl"
    rows = []
    for target in sorted(batch_dir.glob("batch-*.jsonl")):
        rows.extend(
            line for line in target.read_text(encoding="utf-8").splitlines() if line.strip()
        )
    merged.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    print(f"merged={len(rows)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
