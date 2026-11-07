#!/usr/bin/env python3
"""Convert a private acceptance workbook into a local evaluation dataset.

The workbook (question sheet + grading sheet + domain sheet) is a private
instrument: its text never enters the public repository. This converter writes
a deterministic JSONL dataset and a manifest under the local data root, so the
same workbook always produces byte-identical output.

Usage:
    python scripts/import_eval_xlsx.py --xlsx <path> --out-dir <dir> [--seed TEXT]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

QUESTION_HEADERS = [
    "编号",
    "群体",
    "细分身份",
    "海域分区",
    "作业场景",
    "问题（渔民原话）",
    "主要意图",
    "知识域",
    "类型",
    "可答性",
    "核验要点",
    "简要参考答案",
    "依据doc_id",
    "条文/来源定位",
    "难度",
    "评测维度",
    "备注",
]
POINT_HEADERS = [
    "编号",
    "评测维度",
    "可答性",
    "必含要点",
    "数字/口径锚点",
    "常见错误",
    "引用要求（doc_id＋定位）",
    "满分条件",
    "扣分项",
]
DOMAIN_HEADERS = ["域编码", "一级域", "二级主题", "题目数", "主要依据 doc_id", "备注"]

DOMAIN_SHEET = "知识域体系"
DOMAIN_END_MARKERS = ("术语与简称",)
UNREGISTERED = "未登记"
POINT_MARKERS = "①②③④⑤⑥⑦⑧⑨⑩"
SPLIT_DEV = 256
DEFAULT_SEED = "scs-fkb-acceptance-2026-11-07"
EMPTY_ANCHORS = {"", "-", "—", "–", "无", "不适用", "n/a", "N/A"}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _split_list(value: Any, *, separators: str = r"[;；\n]") -> list[str]:
    raw = _text(value)
    if raw in EMPTY_ANCHORS:
        return []
    parts = [part.strip() for part in re.split(separators, raw)]
    return [part for part in parts if part]


def _split_points(value: Any) -> list[str]:
    raw = _text(value)
    if not raw:
        return []
    parts = re.split(rf"[{POINT_MARKERS}]", raw)
    points = [part.strip().strip("。；;，,") for part in parts if part.strip()]
    return points


def _sheet_rows(sheet: Any, headers: list[str], sheet_name: str) -> list[dict[str, Any]]:
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise ValueError(f"sheet {sheet_name!r} is empty")
    header = [_text(cell) for cell in rows[0]]
    if header[: len(headers)] != headers:
        raise ValueError(
            f"sheet {sheet_name!r} header mismatch: "
            f"expected {headers}, got {header[: len(headers)]}"
        )
    records: list[dict[str, Any]] = []
    for row in rows[1:]:
        if not row or not _text(row[0]):
            continue
        values = [_text(cell) for cell in row[: len(headers)]]
        values += [""] * (len(headers) - len(values))
        records.append(dict(zip(headers, values, strict=True)))
    return records


def load_domains(sheet: Any) -> dict[str, str]:
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise ValueError(f"sheet {DOMAIN_SHEET!r} is empty")
    header = [_text(cell) for cell in rows[0]][: len(DOMAIN_HEADERS)]
    if header != DOMAIN_HEADERS:
        raise ValueError(f"sheet {DOMAIN_SHEET!r} header mismatch: got {header}")
    mapping: dict[str, str] = {}
    for row in rows[1:]:
        code = _text(row[0]) if row else ""
        name = _text(row[1]) if len(row) > 1 else ""
        if code in DOMAIN_END_MARKERS or name in DOMAIN_END_MARKERS:
            break
        if code.startswith("KD-") and name:
            mapping[name] = code
    if not mapping:
        raise ValueError(f"sheet {DOMAIN_SHEET!r} has no knowledge-domain rows")
    return mapping


def _split_assignment(ids: list[str], seed: str) -> dict[str, str]:
    ordered = sorted(ids, key=lambda item: hashlib.sha1(f"{seed}|{item}".encode()).hexdigest())
    return {item: ("dev" if index < SPLIT_DEV else "holdout") for index, item in enumerate(ordered)}


def build_dataset(
    questions: list[dict[str, Any]],
    points: list[dict[str, Any]],
    domains: dict[str, str],
    *,
    seed: str = DEFAULT_SEED,
) -> list[dict[str, Any]]:
    points_by_id = {row["编号"]: row for row in points}
    if len(points_by_id) != len(points):
        raise ValueError("grading sheet has duplicate question ids")
    question_ids = [row["编号"] for row in questions]
    if len(set(question_ids)) != len(question_ids):
        raise ValueError("question sheet has duplicate ids")
    unknown = sorted(set(points_by_id) - set(question_ids))
    if unknown:
        raise ValueError(f"grading sheet has unknown ids: {unknown[:5]}")
    missing_points = sorted(set(question_ids) - set(points_by_id))
    if missing_points:
        raise ValueError(f"grading sheet is missing ids: {missing_points[:5]}")
    domain_names = {row["知识域"] for row in questions}
    unknown_domains = sorted(name for name in domain_names if name not in domains)
    if unknown_domains:
        raise ValueError(f"unknown knowledge domains: {unknown_domains}")

    assignment = _split_assignment(question_ids, seed)
    dataset: list[dict[str, Any]] = []
    for row in questions:
        identifier = row["编号"]
        point = points_by_id[identifier]
        doc_ids = _split_list(row["依据doc_id"], separators=r"[;；]")
        dataset.append(
            {
                "id": identifier,
                "persona": row["群体"],
                "role_detail": row["细分身份"],
                "sea_area": row["海域分区"],
                "scenario": row["作业场景"],
                "question": row["问题（渔民原话）"],
                "intent": row["主要意图"],
                "domain": row["知识域"],
                "domain_code": domains[row["知识域"]],
                "doc_type": row["类型"],
                "answerability": row["可答性"],
                "required_points": _split_points(point["必含要点"]),
                "numeric_anchors": _split_list(point["数字/口径锚点"], separators=r"[;；\n]"),
                "common_errors": _split_list(point["常见错误"], separators=r"[;；\n]"),
                "citation_requirement": point["引用要求（doc_id＋定位）"],
                "full_score": point["满分条件"],
                "deductions": point["扣分项"],
                "difficulty": row["难度"],
                "dimension": row["评测维度"],
                "verification_points": row["核验要点"],
                "reference_answer": row["简要参考答案"],
                "doc_locations": _split_list(row["条文/来源定位"], separators=r"[;；\n]"),
                "scs_doc_ids": [item for item in doc_ids if item],
                "unregistered": UNREGISTERED in doc_ids,
                "notes": row["备注"],
                "split": assignment[identifier],
                "review_status": "instrument",
                "reference_answer_reviewed": False,
            }
        )
    dataset.sort(key=lambda item: item["id"])
    return dataset


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_dataset(
    dataset: list[dict[str, Any]],
    *,
    out_dir: Path,
    source: Path,
    seed: str,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in dataset
    ]
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    dataset_path = out_dir / "dataset.jsonl"
    dataset_path.write_bytes(payload)
    counts = {
        "questions": len(dataset),
        "dev": sum(1 for row in dataset if row["split"] == "dev"),
        "holdout": sum(1 for row in dataset if row["split"] == "holdout"),
    }
    manifest = {
        "schema_version": 1,
        "instrument": "acceptance",
        "seed": seed,
        "source": {"name": source.name, "sha256": _sha256_file(source)},
        "dataset": {
            "file": "dataset.jsonl",
            "sha256": _sha256_bytes(payload),
            "bytes": len(payload),
            "rows": counts["questions"],
            "dev": counts["dev"],
            "holdout": counts["holdout"],
        },
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def import_workbook(xlsx: Path, out_dir: Path, *, seed: str = DEFAULT_SEED) -> dict[str, Any]:
    from openpyxl import load_workbook

    workbook = load_workbook(xlsx, data_only=True)
    for name in ("验收集", "判分要点", DOMAIN_SHEET):
        if name not in workbook.sheetnames:
            raise ValueError(f"workbook is missing sheet {name!r}: {workbook.sheetnames}")
    questions = _sheet_rows(workbook["验收集"], QUESTION_HEADERS, "验收集")
    points = _sheet_rows(workbook["判分要点"], POINT_HEADERS, "判分要点")
    domains = load_domains(workbook[DOMAIN_SHEET])
    dataset = build_dataset(questions, points, domains, seed=seed)
    return write_dataset(dataset, out_dir=out_dir, source=xlsx, seed=seed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xlsx", required=True, help="private acceptance workbook")
    parser.add_argument("--out-dir", required=True, help="private dataset directory")
    parser.add_argument("--seed", default=DEFAULT_SEED, help="strategy digest seed")
    args = parser.parse_args(argv)
    try:
        manifest = import_workbook(Path(args.xlsx), Path(args.out_dir), seed=args.seed)
    except (OSError, ValueError) as exc:
        print(f"import failed: {exc}", file=sys.stderr)
        return 2
    data = manifest["dataset"]
    print(
        f"{data['rows']} questions ({data['dev']} dev / {data['holdout']} holdout), "
        f"dataset {data['sha256'][:12]}, source {manifest['source']['sha256'][:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
