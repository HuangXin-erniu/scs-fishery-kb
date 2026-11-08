"""Audit whether indexed documents already answer questions whose expected documents are missing.

The audit is evidence-based: a question is mappable only when the model names a
clause that contains the fact asked (a value, deadline, procedure or responsible
body), not merely the topic. Results feed the point-coverage ceiling so the 0.80
line is either shown to be reachable or the gap is quantified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

PROMPT_VERSION = "evidence-audit-v1"
MAX_DOCS = 3
MAX_CHUNKS_PER_DOC = 2
MAX_CHARS = 6000

AUDIT_SYSTEM = (
    "你是证据审计器。给定一个渔民问题和一组候选证据，判断这些证据是否直接包含问题所问的"
    "具体事实：数值、期限、比例、办理层级、材料、责任主体或处罚幅度。\n"
    "只与主题相关不算可答；证据只覆盖部分子问题算部分可答；完全没有相关条款算不可答。\n"
    "如果可答，必须指出具体条款（doc_id 与 section）并在 reason 里引用该条款的关键句。\n"
    '只输出 JSON：{"answerable": "full|partial|none", "doc_id": "", "section": "", '
    '"reason": ""}'
)

ANSWERABLE = {"full", "partial"}


def _payload(data_root: Path, question: str, evidence: list[Any]) -> str:
    blocks: list[str] = []
    used = 0
    for hit in evidence:
        chunk = hit.chunk
        section = f" §{chunk.section}" if chunk.section else f" p.{chunk.page}"
        text = " ".join(chunk.text.split())[:900]
        block = f"[{chunk.doc_id}{section}] {text}"
        if used + len(block) > MAX_CHARS:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


def _group(hits: list[Any]) -> list[Any]:
    """Keep the best few clauses per document, at most MAX_DOCS documents."""
    by_doc: dict[str, list[Any]] = {}
    for hit in hits:
        by_doc.setdefault(hit.chunk.doc_id, []).append(hit)
    ordered = sorted(by_doc.values(), key=lambda items: -max(item.score for item in items))
    return [item for items in ordered[:MAX_DOCS] for item in items[:MAX_CHUNKS_PER_DOC]]


def _audit_one(question: str, evidence: list[Any], client: Any, cache: Any) -> dict[str, Any]:
    payload = _payload(Path("."), question, evidence)
    key = hashlib.sha256(
        f"{PROMPT_VERSION}\n{question}\n{payload}\n{client.config.model}".encode()
    ).hexdigest()
    cached = cache.get(f"audit-{key[:24]}.json") if cache is not None else None
    if cached is not None:
        return cached
    messages = [
        {"role": "system", "content": AUDIT_SYSTEM},
        {
            "role": "user",
            "content": f"问题：\n{question}\n\n候选证据：\n{payload}\n\n按 JSON 输出。",
        },
    ]
    from scs_fkb.llm import parse_json_object

    value = parse_json_object(client.chat(messages, max_tokens=900))
    if cache is not None:
        cache.put(f"audit-{key[:24]}.json", value)
    return value


def _judgeable_points(row: dict[str, Any]) -> int:
    from scs_fkb.eval_accept.points import point_specs

    specs = point_specs(row, concepts=_concepts(), overrides=_overrides())
    return sum(1 for spec in specs if spec.terms or spec.rule)


_CONCEPTS: Any = None
_OVERRIDES: Any = None


def _concepts() -> Any:
    global _CONCEPTS
    if _CONCEPTS is None:
        from scs_fkb.eval_accept.points import ConceptSource

        data = Path(os.environ["SCS_FKB_DATA_ROOT"]) / "eval/acceptance"
        _CONCEPTS = ConceptSource.load("configs/terms.yaml", data / "domain-terms.yaml")
    return _CONCEPTS


def _overrides() -> Any:
    global _OVERRIDES
    if _OVERRIDES is None:
        from scs_fkb.eval_accept.points import PointOverrides

        data = Path(os.environ["SCS_FKB_DATA_ROOT"]) / "eval/acceptance"
        _OVERRIDES = PointOverrides.load(data / "point-overrides.yaml")
    return _OVERRIDES


def ceiling(
    points_by_question: dict[str, int],
    mappable: set[str],
    *,
    reachable_points: int,
    answerable_points: int,
    all_points: int,
) -> dict[str, float]:
    """Coverage ceilings under both denominators.

    Refusal questions carry required points but must abstain, so their points can
    never be covered; the protocol line is a coverage figure over questions that
    should be answered.
    """
    mapped = reachable_points + sum(points_by_question.get(key, 0) for key in mappable)
    return {
        "reachable_points": reachable_points,
        "mapped_points": mapped,
        "answerable_points": answerable_points,
        "all_points": all_points,
        "ceiling_all_current": round(reachable_points / all_points, 4),
        "ceiling_answerable_current": round(reachable_points / answerable_points, 4),
        "ceiling_all_mapped": round(mapped / all_points, 4),
        "ceiling_answerable_mapped": round(mapped / answerable_points, 4),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("SCS_FKB_DATA_ROOT", ""))
    parser.add_argument("--out", default="")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args(argv)
    if not args.data_root:
        print("set --data-root or SCS_FKB_DATA_ROOT", file=sys.stderr)
        return 2
    data_root = Path(args.data_root).expanduser()
    acceptance = data_root / "eval/acceptance"
    dataset = [json.loads(line) for line in (acceptance / "dataset.jsonl").open()]
    docmap = _load_docmap(acceptance / "doc-map.yaml")

    from scs_fkb.retrieve_v2 import build_retriever

    retriever = build_retriever(data_root, reranker=False)
    from scs_fkb.llm import LLMClient, LLMConfig
    from scs_fkb.rag import LLMCache

    client = LLMClient(LLMConfig.from_env())
    cache = LLMCache(data_root / "llm-cache")

    rows = [row for row in dataset if row["answerability"] in ("可答", "部分可答")]
    unreachable = [row for row in rows if not _reachable(row, docmap)]
    print(f"auditing {len(unreachable)} unreachable questions", file=sys.stderr)

    def work(row: dict[str, Any]) -> dict[str, Any]:
        hits = _group(retriever.search(str(row["question"]), top_k=10))
        try:
            decision = _audit_one(str(row["question"]), hits, client, cache)
        except Exception as exc:  # noqa: BLE001 - an audit failure is data
            decision = {"answerable": "none", "doc_id": "", "section": "", "reason": f"error:{exc}"}
        return {
            "id": row["id"],
            "question": row["question"],
            "domain": row["domain"],
            "expected": row["scs_doc_ids"],
            "decision": decision,
            "candidates": [hit.chunk.doc_id for hit in hits],
        }

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for index, item in enumerate(pool.map(work, unreachable), start=1):
            results.append(item)
            if index % 10 == 0:
                print(f"audited {index}/{len(unreachable)}", file=sys.stderr)

    out_dir = Path(args.out or (Path(os.environ.get("SCS_FKB_RUN_ROOT", ".")) / "P11-MAP-172"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in results) + "\n",
        encoding="utf-8",
    )

    points_by_question = {row["id"]: _judgeable_points(row) for row in unreachable}
    mappable = {
        item["id"] for item in results if str(item["decision"].get("answerable")) in ANSWERABLE
    }
    reachable_points = sum(_judgeable_points(row) for row in rows if _reachable(row, docmap))
    answerable_points = sum(_judgeable_points(row) for row in rows)
    stats = ceiling(
        points_by_question,
        mappable,
        reachable_points=reachable_points,
        answerable_points=answerable_points,
        all_points=849,
    )
    summary = {
        "unreachable": len(unreachable),
        "mappable": len(mappable),
        "full": sum(1 for item in results if item["decision"].get("answerable") == "full"),
        "partial": sum(1 for item in results if item["decision"].get("answerable") == "partial"),
        "mappable_points": sum(points_by_question[key] for key in mappable),
        **stats,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def _load_docmap(path: Path) -> dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))["mapping"]


def _reachable(row: dict[str, Any], docmap: dict[str, Any]) -> bool:
    indexed = _indexed()
    docs: set[str] = set()
    for source_id in row["scs_doc_ids"]:
        entry = docmap.get(source_id) or {}
        if entry.get("covers") in ("full", "partial"):
            docs |= set(entry.get("docs") or [])
    return bool(docs & indexed)


_INDEXED: set[str] | None = None


def _indexed() -> set[str]:
    global _INDEXED
    if _INDEXED is None:
        data = Path(os.environ["SCS_FKB_DATA_ROOT"]) / "v2/processed/chunks.jsonl"
        _INDEXED = {json.loads(line)["doc_id"] for line in data.open()}
    return _INDEXED


if __name__ == "__main__":
    raise SystemExit(main())
