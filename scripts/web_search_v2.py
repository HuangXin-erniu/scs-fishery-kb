#!/usr/bin/env python3
"""Search, fetch and cache web evidence for one question."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

from scs_fkb.config import REPO_ROOT
from scs_fkb.web_v2 import build_provider, load_allowlist, search_web
from scs_fkb.web_v2.policy import provider_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True)
    parser.add_argument("--nature", default="rule")
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--allowlist", default=str(REPO_ROOT / "configs" / "web-sources.yaml"))
    parser.add_argument("--searxng-url", default=os.environ.get("SEARXNG_URL", ""))
    parser.add_argument("--max-results", type=int, default=3)
    parser.add_argument("--explicit", action="store_true")
    args = parser.parse_args(argv)
    if not args.data_root:
        print("error: set SCS_FKB_DATA_ROOT or pass --data-root", file=sys.stderr)
        return 2
    allowlist = load_allowlist(Path(args.allowlist))
    settings = provider_settings(yaml.safe_load(Path(args.allowlist).read_text(encoding="utf-8")))
    provider = build_provider(
        args.searxng_url or settings["searxng_url"],
        fallback=settings["fallback"],
        timeout=settings["timeout_seconds"],
        backend=settings["backend"],
    )
    result = search_web(
        args.question,
        nature=args.nature,
        allowlist=allowlist,
        provider=provider,
        data_root=Path(args.data_root),
        max_results=args.max_results,
        explicit=args.explicit,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
