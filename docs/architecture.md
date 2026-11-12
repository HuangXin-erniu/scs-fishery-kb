# Architecture

> **中文摘要**：SCS-FKB 当前的运行管线是"注册语料 → 抓取/解析 → 条款切分 → 混合索引 →
> 查询改写检索 → 多作答臂 → v3 契约 → 验收工装"。已注册 100 份来源、索引 58 份文档；
> 512 题验收上误答 0.0857、拒答渠道 0.9143、时效 0.9298 已达标；要点覆盖 0.6574、
> 引用 0.5606、口径 0.2105 受证据上限约束（词级上限 0.8556，0.80 需覆盖支持点的 93.6%）。
> 数据、索引与运行产物只在本机，不进入公开仓库。

- Status: current pipeline, documented 2026-11-09. The previous v1 answer/evaluation
  stack is still present in the tree and is scheduled for removal; this document
  describes what actually runs.
- Scope: governed corpus, retrieval, evidence-grounded answering, answer-contract
  fields and acceptance evaluation.
- Non-goals: forecast-model training, raw environmental feeds, vessel tracks and a
  multi-tenant platform.

## 1. Pipeline

```
configs/corpus.yaml (100 sources, schema v4)
   → raw/ snapshots (SHA-256 per source, local only)
   → parsers/ (PDF, HTML, DOCX) → Page(number, text, lines)
   → ingest_v2.chunking (article/section groups, labels, parents)
   → data/v2/processed/{chunks,parents,documents}.jsonl
   → index_v2 (LanceDB dense index, bge-small-zh-v1.5 ONNX) + bm25
   → retrieve_v2.HybridRetriever (rewrite → RRF dense+BM25 → top-k)
   → answer arm (single / facet / quotes / dump)
   → answer_v3.compose (conclusion, conditions, as-of, numbers, gap, channel)
   → service_v2 (FastAPI) or scripts/eval_accept.py (acceptance)
```

## 2. Components

| Layer | Modules | Notes |
|---|---|---|
| Registry & governance | `registry.py`, `configs/corpus.yaml`, `configs/schema.yaml` | source schema v4: tier, lifecycle, provenance, currency |
| Capture | `scripts/capture_source.py` | HTTPS by default, allowlist, provenance and sha256, no overwrite |
| Parsing | `parsers/` | PDF pages, HTML main text, DOCX paragraphs; page numbers preserved |
| Chunking | `ingest_v2/chunking.py`, `chunking.py` | article → section → fallback groups; `label_sections` gives every chunk an article/heading/page label; parent blocks per section |
| Index | `index_v2/` | LanceDB table over child chunks; model bge-small-zh-v1.5 (ONNX); model and chunk digest recorded in the manifest |
| Retrieval | `retrieve_v2/` | rewrite (cached, 2–3 normative queries), RRF fusion, optional cross-encoder (measured and disabled) |
| Answering | `answer_v3/` | **`standard_arm`** (default: bounded evidence pack, structured JSON, citation/number/support checks, cache), `llm_answer`, `facet_arm`, `quotes_arm`, `dump_arm` (Track A) |
| Contract | `answer_v3/compose.py` | three states, conclusion first, as-of, numeric basis, gap and channel |
| Service | `service_v2/` | `/v1` query API, v3 response fields; the dump arm decides answerability from the summary's candidate set, other arms may use the evidence-sufficiency judge (`SCS_FKB_VERIFY_ANSWERS=on`) |
| Evaluation | `eval_accept/`, `scripts/eval_accept.py` | 512-question acceptance instrument, deterministic scoring, per-domain report |

## 3. Answer arms (measured on 512)

| Arm | Mode | Coverage | Citation | Notes |
|---|---|---:|---:|---|
| single | `SCS_FKB_ANSWER_MODE=llm` | 0.3807 | 0.3287 | conclusion + conditions from one pass |
| facet | `SCS_FKB_ANSWER_MODE=facet` | 0.4133 | 0.3540 | decompose, per-facet answer, merge, verify |
| quotes | `SCS_FKB_ANSWER_MODE=quotes` | 0.5437 (120 pilot) | 0.5437 | verbatim quotes, rejected when reworded |
| dump | `SCS_FKB_ANSWER_MODE=dump` | **0.8092** | **0.9565** | deterministic, block quoting, numeric comparison block, no model call; Track A instrument only |
| **standard** | `SCS_FKB_ANSWER_MODE=standard` | Track B (see evaluation) | Track B (see evaluation) | top-50 → rerank top-8 → 12k evidence pack → structured JSON → citation/number/support checks → cache; product default |

The **standard arm is the product default** (`SCS_FKB_ANSWER_MODE=standard`, P26 Phase 1):
it retrieves a 50-candidate pool, reranks to 8, builds a bounded 12k-character
evidence pack, asks for structured JSON, validates every citation/number/claim
and writes a validated answer to the semantic cache. The clause-dump arm is kept
for the Track A instrument only (`SCS_FKB_ANSWER_MODE=dump`), with depth 300,
block quoting, 300 hits / 100,000 characters and the numeric comparison block;
`SCS_FKB_DUMP_DEPTH`, `SCS_FKB_DUMP_MODE`, `SCS_FKB_DUMP_HITS`,
`SCS_FKB_DUMP_CHARS` and `SCS_FKB_DUMP_NUMBERS` override it.

## 4. Acceptance status (512 questions)

| Line | Value | Target | Status |
|---|---:|---:|---|
| Misanswer (70 refusal) | 0.0000 | ≤0.10 | met |
| Refusal-with-channel | 1.0000 | ≥0.90 | met |
| As-of declaration (57) | 0.9474 | ≥0.90 | met |
| Point coverage (727 answerable) | 0.8092 | 0.80 | met (v2) |
| Citation accuracy | 0.9565 | 0.90 | met (v2) |
| Basis accuracy (17 answered numeric) | 0.9412 | 0.85 | met (v2) |

All six lines pass under acceptance protocol v2 on the 67-document index
(2,797 chunks). The term ceiling is 624 of 727 points (0.8583) and the shipped
clause-dump arm reaches 0.8092 with the 300-hit and 100k-character window. Protocol v2 judges citation
location at document level, gives partial credit to point terms and measures basis
over answered numeric rows; the rules and the v1 comparison are in
[evaluation.md](evaluation.md) sections 25-27.

## 5. Boundaries

- Public repository: code, configs, docs, tests; no data, indexes, run artifacts,
  `.env`, state databases or model caches.
- Private data root: raw snapshots, processed stores, indexes, LLM cache, acceptance
  dataset and doc map, run reports.
- Answers always cite retrieved evidence; numbers are checked against the cited
  clause; unsupported answers abstain with a gap and a channel.

## 6. Operating commands

```bash
# public-tree validation
PYTHONPATH=src python -m scs_fkb check

# build store and index (local data root)
PYTHONPATH=src python scripts/build_v2.py
PYTHONPATH=src python scripts/build_index_v2.py

# retrieval recall
PYTHONPATH=src python scripts/measure_recall.py --models BAAI/bge-small-zh-v1.5 --rewrite

# acceptance (dump arm, sufficiency judge on)
SCS_FKB_VERIFY_ANSWERS=on PYTHONPATH=src python scripts/eval_accept.py \
  --task-id local --llm --llm-arm dump --llm-answerability 可答,部分可答 --llm-workers 6

# service: brief answer by default, full evidence with --full
PYTHONPATH=src python -m scs_fkb ask "2026年南海区伏季休渔从什么时候开始？"
PYTHONPATH=src python -m scs_fkb ask --full "2026年南海区伏季休渔从什么时候开始？"
PYTHONPATH=src python -m scs_fkb serve
# local: / (UI), /demo (test page), /docs (OpenAPI), /metrics (requests/latency)
```

## 7. Known limits

- Retrieval recall@5 is 0.913 on answerable questions with mapped documents; the
  remaining misses are documents or clauses absent from the corpus.
- The acceptance instrument's locations are topic labels; citations that only name
  article numbers often fail location matching. This is the main citation gap.
- The LLM endpoint is slow (10–30 s per answer); the deterministic dump arm is fast
  and is the recommended mode for batch use.
- Shared first-generation helpers are retained because the shipped path still
  imports them: `answer.py` (extractive answer and citation validation),
  `rag.py` (LLM cache), `retrieve.py` (lexical gate), `claims.py` (claim routing),
  `store.py` (JSONL I/O) and `jurisdiction.py` (province routing).
- The CLI was reduced to `ask`, `serve` and `check`; the v1
  ingest/evaluate/statistics/reference/knowledge/FAQ modules and the 48-question
  and v2 evaluation sets were removed in the v1 cleanup.
- The dense index is written per version under `v2/index/versions/<id>/` and
  switched by an atomic `v2/index/current.json`; the previous version stays for
  rollback and the manifest records the code commit and configuration hashes.
- The watch and candidate tooling returned as library modules plus
  `scripts/check_sources.py`, `scripts/watch_sources.py` and
  `scripts/weekly_report.py`, so the CLI stays small and the weekly cycle is
  documented in [operations.md](operations.md).
- The standard arm uses a bounded evidence pack (8–12 items, 12k characters) and
  a semantic answer cache under the local data root; a cache hit is invalidated
  when the index version changes or the entry passes its TTL. Aborted Track A
  reruns on the dump arm are a throughput finding, not a retrieval regression.
- The optional web-evidence layer was rebuilt in `src/scs_fkb/web_v2/` and is off
  by default. It searches an official-host allowlist, fetches over HTTPS with TTL
  caching, and returns at most two labelled leads in `web_leads`; those leads are
  not corpus citations, do not enter the answer text and never decide abstention.
  Nothing is auto-ingested; a promotion draft goes to the candidate queue.
