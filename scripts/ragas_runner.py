#!/usr/bin/env python3
"""Run RAGAS 0.4.x metrics for Track B in an isolated virtual environment.

The main project environment deliberately does not install ``ragas``: ragas
0.4.x pins an older langchain/openai stack and would downgrade the runtime the
service depends on.  Install ``requirements-ragas.txt`` into a separate venv and
run this script with that interpreter:

    "$SCS_FKB_LOCAL/venv-ragas/bin/python" scripts/ragas_runner.py \\
        --input samples.jsonl --output ragas.json --workers 4

Input (one JSON object per line)::

    {"id": "IR-001", "question": "...", "answer": "...",
     "contexts": ["..."], "reference": "..."}

Output: aggregate metric means, per-row scores, error classes and run metadata.
Every metric is scored with the modern RAGAS metric objects via ``ascore``;
``ragas.evaluate`` is not used because it only accepts the legacy metric type.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

SAMPLE_FIELDS = ("id", "question", "answer", "contexts", "reference")
DEFAULT_METRICS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
)


def _parse_env(path: Path) -> None:
    """Load KEY=VALUE lines from the project .env without overriding the env."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class FastEmbedAdapter:
    """Minimal ``BaseRagasEmbedding`` adapter over fastembed (ONNX, no torch)."""

    def __new__(cls, model_name: str, cache_dir: str | None = None, cache: Any = None):
        from ragas.embeddings.base import BaseRagasEmbedding

        class _Adapter(BaseRagasEmbedding):
            def __init__(self) -> None:
                super().__init__(cache=cache)
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

            def embed_text(self, text: str, **kwargs: Any) -> list[float]:
                vector = next(iter(self._model.query_embed([text])))
                return [float(value) for value in vector]

            async def aembed_text(self, text: str, **kwargs: Any) -> list[float]:
                return self.embed_text(text, **kwargs)

        return _Adapter()


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        missing = [field for field in ("id", "question", "answer") if not row.get(field)]
        if missing:
            raise SystemExit(f"{path}: row missing {missing}")
        rows.append(row)
    return rows


def _build_metrics(llm: Any, embeddings: Any, names: tuple[str, ...]) -> dict[str, Any]:
    from ragas.metrics.collections import (
        AnswerCorrectness,
        AnswerRelevancy,
        ContextPrecisionWithReference,
        ContextRecall,
        Faithfulness,
    )

    factories = {
        "faithfulness": lambda: Faithfulness(llm=llm),
        "answer_relevancy": lambda: AnswerRelevancy(llm=llm, embeddings=embeddings),
        "context_precision": lambda: ContextPrecisionWithReference(llm=llm),
        "context_recall": lambda: ContextRecall(llm=llm),
        "answer_correctness": lambda: AnswerCorrectness(llm=llm, embeddings=embeddings),
    }
    unknown = [name for name in names if name not in factories]
    if unknown:
        raise SystemExit(f"unknown metrics: {unknown}")
    return {name: factories[name]() for name in names}


async def _score_one(metric: Any, name: str, row: dict[str, Any]) -> float | None:
    question = str(row["question"])
    answer = str(row["answer"])
    contexts = [str(item) for item in (row.get("contexts") or [])]
    reference = str(row.get("reference") or "")
    if name == "faithfulness":
        result = await metric.ascore(
            user_input=question, response=answer, retrieved_contexts=contexts
        )
    elif name == "answer_relevancy":
        result = await metric.ascore(user_input=question, response=answer)
    elif name == "context_precision":
        result = await metric.ascore(
            user_input=question, reference=reference, retrieved_contexts=contexts
        )
    elif name == "context_recall":
        result = await metric.ascore(
            user_input=question, retrieved_contexts=contexts, reference=reference
        )
    elif name == "answer_correctness":
        result = await metric.ascore(user_input=question, response=answer, reference=reference)
    else:  # pragma: no cover - guarded by _build_metrics
        raise ValueError(f"unknown metric {name}")
    value = getattr(result, "value", None)
    return None if value is None else float(value)


async def _run(args: argparse.Namespace, rows: list[dict[str, Any]]) -> dict[str, Any]:
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory

    _parse_env(Path(args.env_file).expanduser())
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model = args.model or os.environ.get("LLM_MODEL", "").strip()
    if not base_url or not api_key or not model:
        raise SystemExit("missing LLM_BASE_URL / LLM_API_KEY / LLM_MODEL")
    session = (
        os.environ.get("SCS_FKB_LLM_SESSION", "").strip() or f"scs-fkb-ragas-{uuid.uuid4().hex[:8]}"
    )
    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=float(args.timeout),
        max_retries=2,
        default_headers={
            "x-opencode-session": session,
            "User-Agent": "scs-fkb-ragas/0.1",
        },
    )
    cache = None
    if args.cache_dir:
        from ragas.cache import DiskCacheBackend

        cache = DiskCacheBackend(Path(args.cache_dir).expanduser())
    llm = llm_factory(model, client=client, cache=cache, max_tokens=4096, temperature=0)
    embeddings = FastEmbedAdapter(
        args.embedding_model,
        cache_dir=args.embedding_cache_dir,
        cache=cache,
    )
    metrics = _build_metrics(llm, embeddings, tuple(args.metrics))
    semaphore = asyncio.Semaphore(max(1, int(args.workers)))
    errors: list[dict[str, str]] = []

    async def score_row(row: dict[str, Any]) -> dict[str, Any]:
        scores: dict[str, float | None] = {}
        tasks = {
            name: asyncio.create_task(_guarded(metric, name, row, semaphore, errors))
            for name, metric in metrics.items()
        }
        for name, task in tasks.items():
            scores[name] = await task
        return {"id": str(row["id"]), **scores}

    async def _guarded(metric, name, row, sem, errors_list):
        async with sem:
            try:
                return await _score_one(metric, name, row)
            except Exception as exc:  # noqa: BLE001 - report per-metric failure
                errors_list.append(
                    {
                        "id": str(row["id"]),
                        "metric": name,
                        "error": type(exc).__name__,
                        "detail": str(exc)[:300],
                    }
                )
                return None

    started = time.perf_counter()
    per_row = await asyncio.gather(*(score_row(row) for row in rows))
    aggregate: dict[str, dict[str, Any]] = {}
    for name in args.metrics:
        values = [row[name] for row in per_row if row.get(name) is not None]
        aggregate[name] = {
            "mean": round(sum(values) / len(values), 4) if values else None,
            "scored": len(values),
            "missing": len(per_row) - len(values),
        }
    return {
        "engine": "ragas",
        "ragas_version": _ragas_version(),
        "model": model,
        "embedding_model": args.embedding_model,
        "rows": len(rows),
        "metrics": aggregate,
        "per_row": per_row,
        "errors": errors[:50],
        "error_count": len(errors),
        "elapsed_seconds": round(time.perf_counter() - started, 1),
        "session": session,
    }


def _ragas_version() -> str:
    try:
        import ragas

        return str(ragas.__version__)
    except Exception:  # noqa: BLE001 - metadata only
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metrics", default=",".join(DEFAULT_METRICS))
    parser.add_argument("--model", default="")
    parser.add_argument("--embedding-model", default="BAAI/bge-small-zh-v1.5")
    parser.add_argument("--embedding-cache-dir", default="")
    parser.add_argument("--cache-dir", default="")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)
    args.metrics = [name.strip() for name in args.metrics.split(",") if name.strip()]
    rows = _load_rows(Path(args.input))
    if args.limit:
        rows = rows[: args.limit]
    result = asyncio.run(_run(args, rows))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "rows": result["rows"],
        "metrics": result["metrics"],
        "errors": result["error_count"],
        "elapsed_seconds": result["elapsed_seconds"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
