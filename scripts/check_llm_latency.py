#!/usr/bin/env python3
"""Probe the configured LLM endpoint with short/medium/long prompts.

Prints p50/p95 per size and exits non-zero when a long prompt exceeds the
per-call deadline.  The probe is metadata-only: it never prints the API key or
the prompt text.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scs_fkb.llm import LLMClient, LLMConfig, LLMError  # noqa: E402

FILLER = (
    "南海近海渔业管理资料：休渔时间、捕捞许可证、渔船登记、渔具规格、"
    "保护区管理、台风防御、补贴申报。"
)


def _prompt(chars: int) -> list[dict[str, str]]:
    body = (FILLER * (chars // len(FILLER) + 1))[:chars]
    return [
        {
            "role": "user",
            "content": f"以下是一段资料，只回复两个字：正常。\n{body}",
        }
    ]


def _pct(values: list[int], q: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return ordered[index]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=30.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    client = LLMClient(LLMConfig.from_env())
    sizes = {"short": 80, "medium": 3000, "long": 12000}
    report: dict[str, dict[str, object]] = {}
    failed = False
    for name, chars in sizes.items():
        latencies: list[int] = []
        errors: list[str] = []
        for _ in range(max(1, args.repeat)):
            started = time.perf_counter()
            try:
                reply = client.chat(_prompt(chars), max_tokens=16, stage=f"probe_{name}")
                if not reply.strip():
                    errors.append("empty")
            except LLMError as exc:
                errors.append(type(exc).__name__)
            latencies.append(int((time.perf_counter() - started) * 1000))
        report[name] = {
            "chars": chars,
            "calls": len(latencies),
            "p50_ms": _pct(latencies, 0.50),
            "p95_ms": _pct(latencies, 0.95),
            "max_ms": max(latencies),
            "errors": errors,
        }
        if name == "long" and (errors or report[name]["p95_ms"] > args.threshold * 1000):
            failed = True
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for name, row in report.items():
            print(
                f"{name}: p50={row['p50_ms']}ms p95={row['p95_ms']}ms "
                f"max={row['max_ms']}ms errors={row['errors']}"
            )
    if failed:
        print(f"FAIL: long prompt p95 or errors exceed {args.threshold}s", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
