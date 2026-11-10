#!/usr/bin/env python3
"""Validate the sourced FAQ and plain-term files against the indexed chunks.

Every FAQ quote must be a verbatim substring of a chunk in the cited document and
section; every term citation must resolve to such a chunk. A failure is fatal.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from scs_fkb.config import REPO_ROOT
from scs_fkb.index_v2.store import load_chunks_v2
from scs_fkb.kb_v2 import load_faq, load_terms_plain

SPACE_RE = re.compile(r"\s+")


def _normalize(value: str) -> str:
    return SPACE_RE.sub("", value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--faq", default=str(REPO_ROOT / "configs" / "faq.yaml"))
    parser.add_argument("--terms", default=str(REPO_ROOT / "configs" / "terms-plain.yaml"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    chunks = load_chunks_v2(Path(args.data_root))
    by_doc: dict[str, list] = {}
    for chunk in chunks:
        by_doc.setdefault(chunk.doc_id, []).append(chunk)
    faq = load_faq(Path(args.faq))
    terms = load_terms_plain(Path(args.terms))

    errors: list[str] = []
    checked = 0
    for entry in faq:
        for cite in entry.get("citations") or []:
            doc = str(cite.get("doc") or "")
            section = str(cite.get("section") or "")
            quote = _normalize(str(cite.get("quote") or ""))
            candidates = [
                chunk
                for chunk in by_doc.get(doc, [])
                if not section
                or chunk.section.startswith(section)
                or section.startswith(chunk.section)
            ]
            if not candidates:
                errors.append(f"{entry['id']}: no chunk for {doc} {section}")
                continue
            if quote and not any(quote in _normalize(chunk.text) for chunk in candidates):
                errors.append(f"{entry['id']}: quote not found in {doc} {section}")
                continue
            checked += 1
    term_checked = 0
    for entry in terms:
        for cite in entry.get("citations") or []:
            doc = str(cite.get("doc") or "")
            section = str(cite.get("section") or "")
            candidates = [
                chunk
                for chunk in by_doc.get(doc, [])
                if not section
                or chunk.section.startswith(section)
                or section.startswith(chunk.section)
            ]
            if not candidates:
                errors.append(f"{entry['term_id']}: no chunk for {doc} {section}")
                continue
            term_checked += 1

    result = {
        "faq": len(faq),
        "faq_citations": checked,
        "terms": len(terms),
        "term_citations": term_checked,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"faq {result['faq']} citations {checked} terms {result['terms']} "
            f"citations {term_checked} errors {len(errors)}"
        )
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
