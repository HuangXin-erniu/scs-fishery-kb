#!/usr/bin/env python3
"""RAGAS-compatible judge for the deterministic slot arm.

Reference-based metrics (context precision/recall) are reported only for rows
that actually carry a reference answer; empty references are not scored as 0.
Structural labels and question restatements are removed before judging.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from eval_ragas import (  # noqa: E402
    FAITHFULNESS,
    PRECISION,
    RECALL,
    RELEVANCY,
    _contexts,
    _judge,
    _rows,
    normalize_answer,
)

from scs_fkb.answer_v3.slots import answer_with_slots  # noqa: E402
from scs_fkb.llm import LLMClient, LLMConfig  # noqa: E402
from scs_fkb.rag import LLMCache  # noqa: E402
from scs_fkb.service_v2.answer import build_service  # noqa: E402


def _stats(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "range": None, "n": 0}
    return {
        "mean": round(sum(values) / len(values), 4),
        "range": round(max(values) - min(values), 4),
        "n": len(values),
        "unstable": (max(values) - min(values)) > 0.3,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--sample", type=int, default=12)
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()
    root = Path(args.data_root)
    svc = build_service(data_root=root)
    client = LLMClient(LLMConfig.from_env())
    cache = LLMCache(root / "llm-cache")
    rows = _rows(ROOT / "configs" / "eval-public.yaml")
    references = [row for row in rows if row.get("reference_answer")]
    plain = [row for row in rows if not row.get("reference_answer")]
    keep_refs = references[: max(1, min(3, args.sample // 4))]
    rows = (plain[: args.sample - len(keep_refs)] + keep_refs)[: args.sample]
    scores: dict[str, list[float]] = {
        "faithfulness": [],
        "answer_relevancy": [],
        "context_precision": [],
        "context_recall": [],
    }
    n_reference = 0
    per_row: list[dict] = []
    for index, row in enumerate(rows, start=1):
        question = str(row.get("question") or "")
        result = answer_with_slots(question, svc.retriever)
        answer = normalize_answer(result.text, drop_gap=True)
        contexts = _contexts(svc, result)
        reference = str(row.get("reference_answer") or "")
        has_reference = bool(reference.strip())
        n_reference += int(has_reference)
        row_values = {"id": row.get("id"), "has_reference": has_reference}
        for key in ("faithfulness", "answer_relevancy"):
            values = []
            for variant in range(1, args.repeat + 1):
                if key == "faithfulness":
                    value = _judge(
                        client,
                        cache,
                        "faithfulness",
                        FAITHFULNESS,
                        question,
                        answer,
                        contexts,
                        variant=f"v{variant}",
                    )
                else:
                    value = _judge(
                        client,
                        cache,
                        "relevancy",
                        RELEVANCY,
                        question,
                        answer,
                        contexts,
                        variant=f"v{variant}",
                    )
                if value is not None:
                    values.append(value)
            scores[key].extend(values)
            row_values[key] = _stats(values)
        if has_reference:
            for key in ("context_precision", "context_recall"):
                values = []
                for variant in range(1, args.repeat + 1):
                    if key == "context_precision":
                        value = _judge(
                            client,
                            cache,
                            "precision",
                            PRECISION,
                            question,
                            reference,
                            contexts,
                            variant=f"v{variant}",
                        )
                    else:
                        value = _judge(
                            client,
                            cache,
                            "recall",
                            RECALL,
                            question,
                            reference,
                            contexts,
                            variant=f"v{variant}",
                        )
                    if value is not None:
                        values.append(value)
                scores[key].extend(values)
                row_values[key] = _stats(values)
        per_row.append(row_values)
        print(index, row.get("id"), row_values, flush=True)
    report = {
        "arm": "slot",
        "rows": len(rows),
        "n_reference": n_reference,
        "repeat": args.repeat,
        "normalization": "strip labels/question prefix; gap lines excluded from judging",
        "metrics": {key: _stats(values) for key, values in scores.items()},
        "per_row": per_row,
    }
    report.update({f"ragas_{key}": value["mean"] for key, value in report["metrics"].items()})
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_row"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
