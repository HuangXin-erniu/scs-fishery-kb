#!/usr/bin/env python3
"""Capture one candidate document and build a provisional review package.

The operator supplies the document URL and the licence/sensitivity decision.
The script captures under the data root, parses the text, runs the provisional
quality gate and writes a review package. It never edits the register or index.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import date
from pathlib import Path

import yaml

from scs_fkb.candidates import load_candidates
from scs_fkb.parsers import parse_source
from scs_fkb.update.review import review_candidate

REPO_ROOT = Path(__file__).resolve().parents[1]


def _capture_module():
    path = REPO_ROOT / "scripts" / "capture_source.py"
    spec = importlib.util.spec_from_file_location("capture_source", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load capture_source.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["capture_source"] = module
    spec.loader.exec_module(module)
    return module


def _text_chars(path: Path) -> int:
    extension = path.suffix.lower().lstrip(".")
    parsed = parse_source(path, extension)
    return sum(len(line) for page in parsed.pages for line in page.lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--license", dest="license_value", required=True)
    parser.add_argument("--sensitivity", required=True)
    parser.add_argument("--practical-domain", default="other")
    parser.add_argument("--tier", default="")
    parser.add_argument("--class", dest="source_class", default="")
    parser.add_argument("--level", default="")
    parser.add_argument("--document-no", default="")
    parser.add_argument("--published-at", default="")
    parser.add_argument("--candidates", default="configs/candidates.yaml")
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT"))
    parser.add_argument("--run-root", default=os.environ.get("SCS_FKB_RUN_ROOT"))
    parser.add_argument("--today", default=date.today().isoformat())
    args = parser.parse_args(argv)
    if not args.data_root or not args.run_root:
        print("error: set SCS_FKB_DATA_ROOT and SCS_FKB_RUN_ROOT", file=sys.stderr)
        return 2
    candidates = load_candidates(args.candidates)
    candidate = next((item for item in candidates if item.get("id") == args.candidate_id), None)
    if candidate is None:
        print(f"error: candidate not found: {args.candidate_id}", file=sys.stderr)
        return 2
    override = dict(candidate)
    if args.tier:
        override["proposed_tier"] = args.tier
    if args.source_class:
        override["proposed_class"] = args.source_class
    if args.level:
        override["proposed_level"] = args.level
    try:
        capture = _capture_module().capture(
            args.url,
            args.source_id,
            Path(args.data_root),
            slug=args.document_no or "",
        )
    except Exception as exc:  # noqa: BLE001 - capture policy errors are reported
        print(f"capture failed: {exc}", file=sys.stderr)
        return 2
    try:
        text_chars = _text_chars(capture.path)
    except Exception as exc:  # noqa: BLE001 - parse failure is a review reason
        text_chars = 0
        print(f"parse warning: {exc}", file=sys.stderr)
    package = review_candidate(
        override,
        text_chars=text_chars,
        sha256=capture.sha256,
        license_value=args.license_value,
        sensitivity=args.sensitivity,
        practical_domain=args.practical_domain,
        today=date.fromisoformat(args.today),
    )
    output = Path(args.run_root).expanduser().resolve() / "candidates" / args.candidate_id
    output.mkdir(parents=True, exist_ok=True)
    payload = package.to_dict()
    payload["capture"] = {
        "url": capture.url,
        "snapshot": capture.relative,
        "sha256": capture.sha256,
        "bytes": capture.bytes,
        "mime": capture.mime,
        "text_chars": text_chars,
        "document_no": args.document_no,
        "published_at": args.published_at,
    }
    (output / "admission.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"captured: {capture.relative} sha256={capture.sha256[:16]}… text_chars={text_chars}")
    print(f"package: {output / 'admission.json'}")
    if not package.acceptable or package.entry is None:
        print(f"NOT ACCEPTABLE: {list(package.quality.reasons)}", file=sys.stderr)
        return 1
    print("\n# provisional entry (review, then add to configs/corpus.yaml)\n")
    print(yaml.safe_dump(package.entry, allow_unicode=True, sort_keys=False))
    print(
        "# next: human review -> add the entry -> "
        "PYTHONPATH=src python scripts/build_v2.py && "
        "PYTHONPATH=src python scripts/build_index_v2.py"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
