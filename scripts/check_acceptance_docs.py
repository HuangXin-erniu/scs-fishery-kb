#!/usr/bin/env python3
"""Check that the acceptance documents carry the canonical facts.

The acceptance package has repeatedly drifted (source counts, index ids, test
counts and the pool result were updated in one document but not the others).
This checker reads ``configs/acceptance.yaml`` and enforces two simple rules:

* every string under ``required`` must appear in the named file;
* every string under ``forbidden`` must not appear in the named file.

It is intentionally substring-based: the config is the single place that names
the canonical numbers, and the documents must quote them verbatim.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def _text(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(f"acceptance document not found: {relative}")
    return path.read_text(encoding="utf-8")


def check(root: Path, config_path: Path) -> list[str]:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    errors: list[str] = []
    for relative, needles in (payload.get("required") or {}).items():
        text = _text(root, relative)
        for needle in needles or []:
            if str(needle) not in text:
                errors.append(f"{relative}: missing required text: {needle!r}")
    for relative, needles in (payload.get("forbidden") or {}).items():
        text = _text(root, relative)
        for needle in needles or []:
            if str(needle) in text:
                errors.append(f"{relative}: stale text still present: {needle!r}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/acceptance.yaml")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        errors = check(root, Path(args.config))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        print(f"acceptance docs check failed: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("acceptance docs check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
