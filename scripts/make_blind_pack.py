#!/usr/bin/env python3
"""Build a blind review pack: question, delivered answer, and the cited source text.

The reviewer must be able to check ``citation_ok`` inside the pack, so every
citation is followed by the verbatim passage it points at.  The pack carries no
record id, no reference answer, no detector flag and no model label; the
sample-number to id map is written to ``key.json`` and stays with the project.

Usage:
    python3 scripts/make_blind_pack.py \
        --answers answers.jsonl \
        --chunks data/v2/processed/chunks.jsonl \
        --docs data/v2/processed/documents.jsonl \
        --out-dir /tmp/pack --seed 20261118

``answers.jsonl`` rows need ``id``, ``question``, ``visible_answer`` and
``citations`` (``doc_id`` plus ``section``; ``page`` is optional).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from collections import defaultdict
from pathlib import Path


def _rows(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def clean_section(section: str) -> str:
    """Drop page noise glued onto a section label and cap its length."""
    text = _squash(section)
    text = re.sub(r"\s+p\.\s*\d+\s*$", "", text)
    text = re.sub(r"^p\.\s*\d+\s+(?=第)", "", text)
    text = re.sub(r"^p\.\s*\d+\s+", "", text)
    text = re.sub(r"\s*§\s*p\.\s*\d+", "", text)
    if len(text) > 120:
        text = text[:120].rstrip("，,；; ") + "…"
    return text


def label(doc_id: str, section: str, page: object = None) -> str:
    section = clean_section(str(section or ""))
    if not section and page not in (None, ""):
        section = f"p.{page}"
    return f"{doc_id} §{section}" if section else doc_id


def _norm(text: str) -> str:
    return re.sub(r"[\s、,，.。;；:：]", "", text or "")


def _article_token(section: str) -> str:
    match = re.search(r"第[一二三四五六七八九十百零〇\d]+条", section or "")
    return match.group(0) if match else ""


def pick_chunks(chunks: dict[str, list[dict]], doc_id: str, section: str) -> list[dict]:
    rows = chunks.get(doc_id) or []
    target = _norm(clean_section(section)).rstrip("…")
    if not target:
        return []
    hits = [row for row in rows if target and target in _norm(str(row.get("section", "")))]
    if not hits and len(target) > 40:
        head = target[:40]
        hits = [row for row in rows if head in _norm(str(row.get("section", "")))]
    if hits:
        return hits[:2]
    hits = [row for row in rows if _norm(str(row.get("section", "")))[:24] == target[:24]]
    if hits:
        return hits[:2]
    token = _article_token(clean_section(section))
    if token:
        hits = [
            row
            for row in rows
            if token in str(row.get("text", "")) or token in str(row.get("section", ""))
        ]
        if hits:
            return hits[:2]
    return []


def _sentences(text: str) -> list[str]:
    body = _squash(text)
    parts = re.split(r"(?<=[。；;！？])", body)
    return [part for part in parts if part.strip()]


def excerpt(text: str, limit: int = 1200, points: list[str] | None = None) -> str:
    """Prefer the sentences that carry the answer's required points.

    A head-of-chunk cut hides table values and mid-page clauses, which is what the
    reviewers flagged as "the conclusion is not visible in the excerpt".  When
    points are available, take the sentence containing each point plus its
    neighbours, in document order, and fall back to the head only if nothing hits.
    """
    sents = _sentences(text)
    body = _squash(text)
    if len(body) <= limit:
        return body
    wanted: set[int] = set()
    for point in points or []:
        token = _norm(point)
        if len(token) < 2:
            continue
        for index, sentence in enumerate(sents):
            if token in _norm(sentence) or _norm(sentence) in token:
                wanted.add(index)
                if index > 0:
                    wanted.add(index - 1)
                if index + 1 < len(sents):
                    wanted.add(index + 1)
    if wanted:
        chosen: list[str] = []
        used = 0
        for index in sorted(wanted):
            sentence = sents[index]
            if used + len(sentence) > limit and chosen:
                break
            chosen.append(sentence)
            used += len(sentence)
        if chosen:
            return "".join(chosen)
    cut = body[:limit].rstrip("，,；;。 ")
    return cut + "…"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--chunks", required=True)
    parser.add_argument("--docs", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--title", default="盲评包")
    parser.add_argument("--seed", type=int, default=20261118)
    parser.add_argument("--n", type=int, default=0, help="keep only the first n answers")
    parser.add_argument("--questions", default="", help="questions CSV with required_points")
    parser.add_argument(
        "--strict", action="store_true", help="fail if a citation cannot be located"
    )
    args = parser.parse_args(argv)

    points_by_id: dict[str, list[str]] = {}
    if args.questions:
        with Path(args.questions).open(encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                points_by_id[str(row.get("id", ""))] = [
                    part.strip()
                    for part in str(row.get("required_points", "")).split("；")
                    if part.strip()
                ]
    answers = _rows(Path(args.answers))
    if args.n:
        answers = answers[: args.n]
    chunks: dict[str, list[dict]] = defaultdict(list)
    for row in _rows(Path(args.chunks)):
        chunks[str(row.get("doc_id", ""))].append(row)
    docs = {str(row.get("doc_id", "")): row for row in _rows(Path(args.docs))}

    order = list(range(len(answers)))
    random.Random(args.seed).shuffle(order)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pack_path = out / "blind-pack.md"
    lines = [
        f"# {args.title}",
        "",
        "> 每题给出：问题、当前答复、答复所引依据的原文摘录。",
        "> 判定只看这三样，不参考检测器标记、旧复核记录或我方预判。",
        "> 规则见 `rubric.md`；`citation_ok` 必须能在本题摘录块内核实。",
        "",
    ]
    key: dict[str, str] = {}
    missing: list[str] = []
    for sample_no, index in enumerate(order, 1):
        row = answers[index]
        key[str(sample_no)] = str(row.get("id", ""))
        lines.append(f"## {sample_no}")
        lines.append("")
        lines.append(f"**问：** {_squash(str(row.get('question', '')))}")
        lines.append("")
        lines.append(f"**答：** {_squash(str(row.get('visible_answer', '')))}")
        lines.append("")
        citations = []
        seen_citations: set[tuple[str, str]] = set()
        for citation in row.get("citations") or []:
            cite_key = (
                str(citation.get("doc_id", "")),
                clean_section(str(citation.get("section", ""))),
            )
            if cite_key in seen_citations:
                continue
            seen_citations.add(cite_key)
            citations.append(citation)
        if not citations:
            lines.append("**依据摘录：** 无（答复未引用任何依据）")
        seen_quotes: set[str] = set()
        for citation in citations[:4]:
            doc_id = str(citation.get("doc_id", ""))
            section = str(citation.get("section", ""))
            meta = docs.get(doc_id, {})
            title = meta.get("title") or meta.get("title_zh") or doc_id
            lines.append(
                f"**依据** `{label(doc_id, section, citation.get('page'))}` "
                f"（《{title}》，{meta.get('level', '')}，"
                f"发布 {meta.get('publisher', '')}，"
                f"{str(meta.get('effective_from', ''))[:10] or '时效未标注'}）"
            )
            quoted = 0
            for chunk in pick_chunks(chunks, doc_id, section):
                body = excerpt(
                    str(chunk.get("text", "")),
                    points=points_by_id.get(str(row.get("id", "")), []),
                )
                dedupe = body[:80]
                if dedupe in seen_quotes:
                    quoted += 1
                    continue
                seen_quotes.add(dedupe)
                lines.append("")
                lines.append(f"> {body}")
                quoted += 1
            if not quoted:
                missing.append(str(row.get("id", "")))
                lines.append("")
                lines.append("> （该依据在索引中未能定位，本题不可按此条核实）")
            lines.append("")
        lines.append("---")
        lines.append("")

    pack_path.write_text("\n".join(lines), encoding="utf-8")
    digest = hashlib.sha256(pack_path.read_bytes()).hexdigest()

    with (out / "worksheet.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "sample_no",
                "citation_ok",
                "conclusion_ok",
                "refusal_ok",
                "asof_ok",
                "human_verdict",
                "note",
            ]
        )
        for sample_no in range(1, len(order) + 1):
            writer.writerow([sample_no, "", "", "", "", "", ""])

    (out / "key.json").write_text(
        json.dumps(
            {"seed": args.seed, "pack_sha256": digest, "key": key},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    empty = sum(1 for row in answers if not row.get("citations"))
    print(f"pack: {len(answers)} 题 → {pack_path}")
    print(f"sha256: {digest}")
    if missing:
        print(f"unresolved citations: {len(missing)} ({', '.join(missing[:7])})")
    if args.strict and missing:
        return 2
    print(f"无引用: {empty} 题")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
