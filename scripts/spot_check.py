#!/usr/bin/env python3
"""Spot-check sampling, worksheet generation and scoring.

The acceptance instrument is private: every subcommand takes ``--dataset`` and
``--out`` pointing outside the repository. This script never copies question
text, item ids or run paths into the repository; the public tree only carries
the code.

Three steps, each reproducible from the command line:

``sample``
    Draw a stratified, seeded sample and assert it does not overlap an exclude
    list. Strata default to 10 answerable, 10 partly answerable and 10
    must-refuse rows.
``worksheet``
    Render the sampled rows as a worksheet with the four judgement columns and
    a rubric sheet. CSV is always written; XLSX is written when ``openpyxl`` is
    importable. ``--answers`` merges the system summary and its provenance
    (``model`` / ``fallback`` / ``deterministic``) so a reviewer sees exactly
    what the user sees, and so a silent fallback cannot pass as a model answer.
    ``--doc-map`` resolves the instrument's ``SCS-*`` ids to repository document
    ids and titles, so a reviewer reads "海上交通安全法" rather than "SCS-L-002".
``score``
    Aggregate a filled worksheet into per-line pass rates. Blank or ``NA``
    cells leave the denominator; a ``refusal_ok`` verdict on an answerable row
    is counted as a failure of the refusal line only when the row was expected
    to be answered.

The rubric is not embedded in the data: pass lines are printed by ``score`` so
a report can quote them verbatim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

STRATA = ("可答", "部分可答", "应拒答")
JUDGEMENT_COLUMNS = ("citation_ok", "conclusion_ok", "refusal_ok", "asof_ok")
PASS_LINES = {"citation": 0.95, "conclusion": 0.85, "refusal": 0.90}
RUBRIC = [
    (
        "citation_ok",
        "引用正确",
        "结论与关键数值/期限所在的事实句有可解析引用，且引用文档与期望文档一致或同主题同层级",
    ),
    (
        "conclusion_ok",
        "结论正确",
        "问题问到的核心事实在摘要里直接可读且正确；漏核心事实、答非所问、数值错均判 N",
    ),
    ("refusal_ok", "拒答合理", "应拒答题必须拒答并给出具体受理主体；可答或部分可答被误拒判 N"),
    ("asof_ok", "时效声明", "涉及时间的题写明依据版本或年月；不涉及时填 NA"),
]
WORKSHEET_FIELDS = (
    "id",
    "persona",
    "domain",
    "dimension",
    "answerability",
    "question",
    "expected_docs",
    "summary",
    "summary_source",
    *JUDGEMENT_COLUMNS,
    "note",
)


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def _rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _ids(path: Path | None) -> set[str]:
    if path is None:
        return set()
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return {str(json.loads(line)["id"]) for line in text.splitlines() if line.strip()}
    return {line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")}


def _expected(row: dict[str, Any], docmap: Any = None) -> str:
    docs = [str(item) for item in row.get("scs_doc_ids") or []]
    if docmap is None:
        return ";".join(docs)
    rendered: list[str] = []
    for item in docs:
        entry = docmap.entry(item)
        if entry is None:
            rendered.append(item)
            continue
        target = "/".join(entry.docs) if entry.docs else entry.covers
        rendered.append(f"{item}（{entry.title}；{target}）")
    return ";".join(rendered)


def _digest(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps([str(row.get("id")) for row in rows], ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def cmd_sample(args: argparse.Namespace) -> int:
    dataset = _rows(Path(args.dataset).expanduser())
    if not dataset:
        return _fail(f"empty dataset: {args.dataset}")
    excluded = _ids(Path(args.exclude).expanduser() if args.exclude else None)
    counts = {key: int(value) for key, value in (item.split("=") for item in args.strata)}
    picked: list[dict[str, Any]] = []
    report: dict[str, Any] = {"seed": args.seed, "strata": counts, "excluded": len(excluded)}
    for stratum in STRATA:
        target = counts.get(stratum, 0)
        pool = [row for row in dataset if str(row.get("answerability")) == stratum]
        pool = [row for row in pool if str(row.get("id")) not in excluded]
        pool.sort(key=lambda row: str(row.get("id")))
        rng = random.Random(f"{args.seed}:{stratum}")
        rng.shuffle(pool)
        if len(pool) < target:
            return _fail(f"stratum {stratum} has {len(pool)} rows, needs {target}")
        picked.extend(pool[:target])
    overlap = {str(row.get("id")) for row in picked} & excluded
    if overlap:
        return _fail(f"sample overlaps the exclude list: {sorted(overlap)}")
    ids = sorted(str(row.get("id")) for row in picked)
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (out / "sample.ids").write_text("\n".join(ids) + "\n", encoding="utf-8")
    report.update(
        {
            "size": len(picked),
            "ids_sha256": _digest(picked),
            "personas": dict(Counter(str(row.get("persona")) for row in picked)),
            "domains": dict(Counter(str(row.get("domain")) for row in picked)),
            "disjoint_from_exclude": not overlap,
        }
    )
    (out / "sample.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _write_xlsx(path: Path, rows: list[dict[str, Any]]) -> bool:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment
        from openpyxl.worksheet.datavalidation import DataValidation
    except ImportError:
        return False
    book = Workbook()
    sheet = book.active
    sheet.title = "明细"
    sheet.append(list(WORKSHEET_FIELDS))
    for row in rows:
        sheet.append([row.get(key, "") for key in WORKSHEET_FIELDS])
    width = {
        "question": 48,
        "expected_docs": 36,
        "summary": 72,
        "note": 40,
        "domain": 14,
        "dimension": 12,
    }
    summary_col = WORKSHEET_FIELDS.index("summary") + 1
    for row_index in range(2, len(rows) + 2):
        sheet.cell(row=row_index, column=summary_col).alignment = Alignment(
            wrap_text=True, vertical="top"
        )
    for index, key in enumerate(WORKSHEET_FIELDS, start=1):
        sheet.column_dimensions[sheet.cell(row=1, column=index).column_letter].width = width.get(
            key, 12
        )
    first = WORKSHEET_FIELDS.index(JUDGEMENT_COLUMNS[0]) + 1
    last = WORKSHEET_FIELDS.index(JUDGEMENT_COLUMNS[-1]) + 1
    validation = DataValidation(type="list", formula1='"Y,N,NA"', allow_blank=True)
    sheet.add_data_validation(validation)
    start = sheet.cell(row=2, column=first).coordinate
    end = sheet.cell(row=len(rows) + 1, column=last).coordinate
    span = f"{start}:{end}"
    validation.add(span)
    sheet.freeze_panes = "A2"
    rubric = book.create_sheet("判定口径")
    rubric.append(["列", "判定", "口径"])
    for key, name, rule in RUBRIC:
        rubric.append([key, name, rule])
    rubric.append([])
    rubric.append(["通过线", "引用 ≥95%、结论 ≥85%、拒答 ≥90%"])
    rubric.append(["来源", "source: human 需签字；AI 代演只能标 source: simulated"])
    rubric.append(
        [
            "summary_source",
            "不是判定列",
            "model=模型摘要；fallback=模型草稿未过校验、已退回旧摘要；deterministic=未尝试模型。"
            "评分时报告回退率，回退行不能当作模型摘要计分。",
        ]
    )
    book.save(path)
    return True


def _answers(path: str | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    return {str(row.get("id")): row for row in _rows(Path(path).expanduser())}


def cmd_worksheet(args: argparse.Namespace) -> int:
    dataset = {str(row.get("id")): row for row in _rows(Path(args.dataset).expanduser())}
    answers = _answers(args.answers)
    docmap = None
    if getattr(args, "doc_map", ""):
        from scs_fkb.eval_accept import load_docmap

        docmap = load_docmap(args.doc_map)
    wanted = sorted(_ids(Path(args.ids).expanduser()))
    missing = [item for item in wanted if item not in dataset]
    if missing:
        return _fail(f"ids not in the dataset: {missing}")
    rows: list[dict[str, Any]] = []
    for item in wanted:
        row = dict(dataset[item])
        row["expected_docs"] = _expected(row, docmap)
        answer = answers.get(item) or {}
        row["summary"] = str(answer.get("summary") or "")
        row["summary_source"] = str(answer.get("summary_source") or "")
        rows.append(row)
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    if answers:
        missing_answers = [item for item in wanted if item not in answers]
        if missing_answers:
            return _fail(f"no answer for rows: {missing_answers}")
    with (out / "worksheet.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(WORKSHEET_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in WORKSHEET_FIELDS})
    wrote_xlsx = _write_xlsx(out / "worksheet.xlsx", rows)
    provenance = dict(Counter(row.get("summary_source") or "unset" for row in rows))
    print(
        f"worksheet: {len(rows)} rows, csv=yes, xlsx={'yes' if wrote_xlsx else 'no'}, "
        f"summary_source={provenance}"
    )
    return 0


def _read_worksheet(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _verdict(value: str) -> str:
    text = (value or "").strip().upper()
    return text if text in {"Y", "N", "NA"} else ""


def _rate(rows: list[dict[str, Any]], column: str) -> dict[str, Any]:
    judged = [row for row in rows if _verdict(row.get(column, "")) in {"Y", "N"}]
    hits = sum(1 for row in judged if _verdict(row.get(column, "")) == "Y")
    return {
        "hits": hits,
        "judged": len(judged),
        "rate": round(hits / len(judged), 4) if judged else None,
        "na": sum(1 for row in rows if _verdict(row.get(column, "")) == "NA"),
    }


def cmd_score(args: argparse.Namespace) -> int:
    rows = _read_worksheet(Path(args.worksheet).expanduser())
    answerable = [row for row in rows if row.get("answerability") in {"可答", "部分可答"}]
    refusal = [row for row in rows if row.get("answerability") == "应拒答"]
    result = {
        "rows": len(rows),
        "citation": _rate(answerable, "citation_ok"),
        "conclusion": _rate(answerable, "conclusion_ok"),
        "refusal": _rate(refusal, "refusal_ok"),
        "asof": _rate(rows, "asof_ok"),
        "pass_lines": PASS_LINES,
        "summary_source": dict(Counter(str(row.get("summary_source") or "unset") for row in rows)),
        "unfilled": [
            str(row.get("id"))
            for row in rows
            if any(_verdict(row.get(column, "")) == "" for column in JUDGEMENT_COLUMNS)
        ],
    }
    for key, line in PASS_LINES.items():
        rate = result[key]["rate"]
        result[f"{key}_pass"] = bool(rate is not None and rate >= line)
    fallbacks = [str(row.get("id")) for row in rows if str(row.get("summary_source")) == "fallback"]
    result["fallback_rows"] = fallbacks
    result["fallback_rate"] = round(len(fallbacks) / len(rows), 4) if rows else None
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (out / "scores.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for key in ("citation", "conclusion", "refusal", "asof"):
        item = result[key]
        verdict = (
            "pass"
            if result.get(f"{key}_pass")
            else "miss"
            if key in PASS_LINES and item["rate"] is not None
            else "-"
        )
        print(f"{key:11s} {item['hits']}/{item['judged']} = {item['rate']} ({verdict})")
    if result["unfilled"]:
        print(f"unfilled rows: {len(result['unfilled'])}")
    if result["summary_source"]:
        print(
            f"summary_source {result['summary_source']} "
            f"fallback {len(fallbacks)}/{len(rows)} = {result['fallback_rate']}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sample = sub.add_parser("sample", help="draw a stratified, seeded sample")
    sample.add_argument("--dataset", required=True, help="private instrument JSONL")
    sample.add_argument("--out", required=True, help="output directory outside the repository")
    sample.add_argument("--n", type=int, default=30)
    sample.add_argument("--seed", default="20261111")
    sample.add_argument("--exclude", default="", help="file of ids that must not be drawn")
    sample.add_argument(
        "--strata",
        nargs="*",
        default=["可答=10", "部分可答=10", "应拒答=10"],
        help="stratum=count pairs",
    )
    sample.set_defaults(func=cmd_sample)

    worksheet = sub.add_parser("worksheet", help="render sampled rows as a worksheet")
    worksheet.add_argument("--dataset", required=True)
    worksheet.add_argument("--ids", required=True, help="file of ids, one per line")
    worksheet.add_argument("--out", required=True)
    worksheet.add_argument(
        "--answers", default="", help="optional JSONL with id, summary and summary_source"
    )
    worksheet.add_argument(
        "--doc-map", default="", help="optional doc-map.yaml resolving SCS-* ids to documents"
    )
    worksheet.set_defaults(func=cmd_worksheet)

    score = sub.add_parser("score", help="aggregate a filled worksheet")
    score.add_argument("--worksheet", required=True)
    score.add_argument("--out", required=True)
    score.set_defaults(func=cmd_score)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
