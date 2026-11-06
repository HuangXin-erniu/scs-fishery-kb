# Architecture

> **中文摘要**：本文件描述 SCS-FKB 的分层架构、组件、数据流、数据契约与运行方式。
> 当前 `main` 是 28 文档的混合检索原型；P10 目标架构采用 LlamaIndex + LanceDB + BGE，并区分“正式知识库”与“临时网络证据”两个平面。
> 数据与运行产物只留在本机，不进入公开仓库；所有回答必须基于检索证据并带可核验引用；`restricted` 来源不得发送到外部模型 API。

- Status: framework documented; the P10 governance baseline (source schema v4, two-plane evidence, RAG standard, ADRs) was adopted on 2026-11-06. The running `main` baseline is still the 28-document hybrid prototype with the external facts/notes store; the LlamaIndex/LanceDB/BGE orchestration, controlled web channel and Web service are implemented in the P10 tasks.
- Scope: knowledge-layer corpus, retrieval, evidence-grounded answers, controlled web evidence and evaluation.
- Non-goals: forecast-model training, raw environmental data, full vessel tracks, a production multi-tenant platform and downstream data integration.

## 1. Context

**Users**

- Vessel operators and captains who need operational, policy and fishery-condition knowledge.
- Fisheries administration staff who need definitions, regulations and statistical context.
- Maintainers who ingest sources, evaluate retrieval and operate the service.

**External systems**

- Local source files and tables supplied by data owners.
- A hosted OpenAI-compatible model endpoint for answer generation.
- A future downstream platform that consumes the `/v1` query contract.

**Constraints**

- Local development on a Mac with 8 GB memory; no GPU and no database server.
- No data payloads, indexes, run artifacts or state databases in the public repository.
- Sources may be public, internal or restricted; sensitivity controls where content may go.

## 2. Design principles

1. **Evidence first.** Answers are generated only from retrieved evidence; citations are checked against the retrieved chunks.
2. **Governed sources.** Every source is registered with licence, sensitivity, version and hash before ingestion.
3. **Data locality.** Raw data, processed chunks, indexes and run artifacts stay local.
4. **Reproducibility.** Commands, model identifiers, index versions and evidence hashes are recorded.
5. **Small, replaceable components.** Parsing, retrieval, generation and evaluation are separate modules with clear contracts.
6. **No premature platform.** The project builds a local service and a contract; it does not build a production multi-tenant platform.
7. **Two evidence planes.** Canonical registered sources are versioned, citable and reproducible; live web evidence is ephemeral, labelled and never auto-ingested. The two planes have separate lifecycles and conflict rules.

## 3. Logical architecture

| Layer | Component | Responsibility |
|---|---|---|
| Interface | FastAPI `/v1` + Web UI + CLI | Query, sources, feedback, health; `ingest`, `retrieve`, `ask`, `eval` for operations |
| Orchestration | LlamaIndex pipeline | Ingestion, query pipeline, routing and evaluation adapters |
| Retrieval | Retriever | Normalization, BM25, dense retrieval, RRF, metadata filters, BGE rerank, parent expansion |
| Generation | Answer engine | Prompt construction, claim validation, citation resolution, clarification, abstention and conflict display |
| Knowledge | Knowledge store | Documents, chunks, LanceDB, BM25, facts, playbooks, terms, FAQs and manifest |
| Data | Ingestion | Snapshot, Docling/trafilatura/custom adapters, chunking, table extraction, hashing and quarantine |
| Governance | Source register v4 | Authority tier, level, licence, sensitivity, provenance, effective dates, currency, candidates and lifecycle |
| Web | Ephemeral web channel | SearXNG query, allowlist, fetch, WebEvidence cache/TTL, labels and promotion |
| Evaluation | Evaluation runner | 120-question reviewed set, RAGAS-compatible metrics, deterministic metrics and reports |

## 4. Components and module map

```text
src/scs_fkb/parsers/       html.py, docx.py, ofd.py, pdf.py, doc.py, table.py — format adapters
src/scs_fkb/patterns.py    article, section and chapter expressions
src/scs_fkb/chunking.py    page-aware article, section and fallback chunking
src/scs_fkb/bm25.py        character-bigram BM25 with a sensitivity filter
src/scs_fkb/answer.py      extractive evidence pack, citation validation and abstention
src/scs_fkb/evaluate.py    document-level retrieval, abstention and citation metrics
src/scs_fkb/store.py       processed documents, chunks and manifest
src/scs_fkb/facts.py       fact schema, evidence/conflict checks, external fact documents
src/scs_fkb/terms.py       terminology map, source checks and external term documents
src/scs_fkb/faq.py         public FAQ claims, validation and external FAQ documents
src/scs_fkb/registry.py    source schema v4, currency and watch-coverage checks
src/scs_fkb/cli.py         ingest, retrieve, ask and eval
configs/pipeline.yaml      documents, chunking, retrieval and answer parameters
local data root            raw snapshots, processed data and indexes (outside the repository)
tests/                     configuration, parser, pipeline and public-tree tests
```

P10 target modules replace the orchestration while keeping the proven domain
components: `ingest/loaders.py`, `ingest/pipeline.py`, `ingest/chunking.py`,
`index/{lancedb_store,bm25,embeddings,manifest}.py`,
`retrieve/{router,hybrid,rerank,filters,parent}.py`,
`web/{search,fetch,evidence,policy}.py`,
`knowledge/{facts,playbooks,terms,faq,extract,review}.py`,
`answer/{composer,validator,clarify,conflict}.py`,
`service/{api,schemas,ui}.py` and `eval/{dataset,metrics,ragas_adapter,report}.py`.
The existing `bm25.py`, `answer.py` citation validator and `registry.py`
governance checks are retained behind adapters rather than rewritten.

**Ingestion v2 (2026-11-06).** `src/scs_fkb/ingest_v2/` is a parallel path, not
the default. It snapshots all 63 sources (2,211 files, 142 MB) into the local
data root, builds 28 documents into 745 parent and 785 child chunks with 0 lost
page/section anchors, and writes an incremental manifest. A second build skips
all 28 documents; a changed source rebuilds only itself. Registered HTML/PDF/DOCX
stay on the legacy parsers to preserve anchors; Docling and trafilatura are
optional fallbacks. The live v1 store, index and answer path are unchanged.

**Retrieval v2 (2026-11-06).** `src/scs_fkb/index_v2/` builds a LanceDB table
from the 785 v2 child chunks (98 s, 4.49 GB peak RSS) and exposes it through
LlamaIndex `VectorStoreIndex.from_vector_store`. `src/scs_fkb/retrieve_v2/`
combines the proven BM25 index with the dense ranking through weighted RRF,
applies sensitivity/authority/level/effective-date filters, and optionally
reranks with `bge-reranker-v2-m3-int8` (top-10, 300 chars). On the 31 anchored
questions the no-rerank arm matches the v1 baseline: dev 19/19, test 12/12,
abstention 8/11, P95 16 ms. The reranker improves MRR but loses two anchors and
raises P95 to 2.27 s, so it is disabled by default and enabled with `--rerank`
for calibration. The v1 answer path is not switched.

**Knowledge internalisation (2026-11-06).** `configs/playbooks/` holds 15
persona playbooks with 32 steps, each citing approved facts. The fact layer is
200 entries (80 approved + 120 draft provision facts) and the terminology map is
150 entries (116 approved + 34 draft). `scripts/check_playbooks.py` validates
step references and source ids; `scripts/weekly_update.sh` runs the source,
watch, fact, term and playbook checks and writes a dated report without
ingesting anything.

**Answer service v2 (2026-11-06).** `src/scs_fkb/service_v2/` composes v2 hybrid
retrieval, the extractive answer path, approved facts/playbooks and optional
web evidence behind a FastAPI contract. It is local and single-user, defaulting
to `127.0.0.1`; `SCS_FKB_API_KEY` adds `X-API-Key` enforcement. The Web UI is
server-rendered. A fact lead prepends a precise approved value when its source
chunk is retrieved; the citation validator runs before any answer is returned.

**Evaluation v2 (2026-11-06).** `src/scs_fkb/eval_v2/` holds deterministic
RAGAS-compatible metrics and a runner over 120 questions: 80 dev questions from
approved facts, 30 draft provision test questions and 10 abstention cases. The
test split is report-only. `scripts/eval_v2.py` writes JSON and Markdown under
the run root and exits non-zero when the dev gate fails.

**Web evidence v2 (2026-11-06).** `src/scs_fkb/web_v2/` adds the ephemeral
plane: a SearXNG JSON provider with a DuckDuckGo fallback, allowlist filtering
before any request, HTTPS fetch with `trafilatura` extraction and a PDF fallback,
TTL-aware `WebEvidence` caching, trigger rules, and a promotion draft that never
writes the register. The 20-query smoke produced evidence for 13 queries (32
records), dropped 75 non-allowlisted results and recorded 5 provider failures;
the failures are explicit and do not affect the canonical path. The v1 web-card
path and answer path are unchanged.

The internalised layer is separate from the corpus index. `facts.py` validates 200 facts against the indexed chunks (80 approved + 120 draft; verbatim evidence, register hash, effective dates and conflicts); `terms.py` validates 150 terminology entries; `playbooks.py` validates 15 procedures with 32 fact-cited steps; `faq.py` checks that every FAQ claim resolves to an approved fact. `ingest --external-only` turns the approved records into external documents; the corpus store and its index stay unchanged. The checks run through `facts check`, `terms check` and `faq check`, and none of these records is read by the corpus answer path yet.
Each module exposes a small callable surface rather than a framework. Shared code is extracted only when a second module needs it. The v1 baseline is deterministic: it makes no model call and needs no network access; the P10 target adds local BGE embedding/reranking and a controlled web channel behind separate interfaces. Citations carry a page anchor for the paginated OFD and PDF sources and an article or section anchor for the HTML, DOCX and DOC sources. The ranker is BM25 over character bigrams with an optional title boost, which multiplies a chunk score by 1 + title_boost × the share of query tokens present in the document title. The evaluation compares the top five chunks against gold anchors in `configs/eval.yaml`: a document plus a section prefix, or a document plus a page. Retrieval runs in one of three modes: `bm25`, `dense` or `hybrid`. Hybrid fuses the BM25 and dense rankings with weighted reciprocal-rank fusion (BM25 weight 2.0, dense weight 1.0) and keeps the lexical gate as the only abstention signal, so RRF scores are never compared with BM25 scores. Statistical questions pass through a third, local-only channel: `stats.py` reads the copied indicator table, parses years, region, sea area, gear and indicator cues from the question, filters rows and returns the published values with their edition, table name and basis. The channel never enters the main index or the gate, and it names the two dimensions the yearbooks do not publish rather than substituting one for the other. Definition questions also pass through a reference channel: the terminology bridge in `configs/glossary-bridge.yaml` maps a Chinese term to English concepts, and `reference.py` queries the three CWP pages with those concepts only, returning passages that carry their own citations while the main ranking and its gate stay untouched.

## 5. Data flow

```text
<data_root>/raw
  → source register v4 (authority / level / licence / sensitivity / provenance / currency)
  → content-addressed snapshot
  → parsing (Docling / trafilatura / custom OFD, Excel) and OCR (opt-in)
  → structure-aware chunking and table/indicator extraction
  → <data_root>/v2/processed (documents, chunks, metadata)
  → facts / playbooks / terms / FAQ (verified against chunks)
  → <data_root>/v2/index (LanceDB + BM25 + manifest)
  → query normalization and slot filling
  → hybrid retrieval (BM25 + dense + RRF)
  → metadata, sensitivity and effective-date filtering
  → BGE rerank and parent expansion
  → evidence pack (canonical + optional ephemeral web)
  → claim validation, citations, abstention / clarify / conflict
  → FastAPI / Web UI and run report
```

The canonical ingestion path is offline and repeatable. The canonical query path
is read-only with respect to the index. The ephemeral web path is separate: it
queries SearXNG, fetches allowlisted pages, writes a TTL cache and never writes
the register or the canonical index.

## 6. Data contracts

The machine-readable schema is [configs/schema.yaml](../configs/schema.yaml). The main records are:

**SourceRecord v4**

`id`, `title`, `title_zh`, `publisher`, `year`, `type`, `jurisdiction`, `level`,
`authority_tier`, `source_class`, `format`, `location`, `hash`, `provenance`,
`effective`, `quality`, `supersedes`, `superseded_by`, `license`, `license_note`,
`sensitivity`, `status`, `currency`, `retrieval`, `lifecycle`, `retirement`.
Legacy v3 entries are normalised by the loader; the file-level `schema_version`
stays `1` and `source_record_schema: 4` names the record contract.

**Document**

`doc_id`, `source_id`, `title`, `title_zh`, `publisher`, `year`, `doc_type`, `sensitivity`, `language`, `page_count`, `file_hash`.

**Chunk**

`chunk_id`, `doc_id`, `page`, `section`, `table_id`, `text`, `token_count`, `char_start`, `char_end`.

**Citation**

`doc_id`, `title`, `page`, `section`, `snippet`, `score`.

**Answer**

`answer`, `citations`, `abstained`, `reason`, `mode`, `index_version`, `model`,
`web_evidence`, `conflicts`, `clarification`, `latency_ms`.

**WebEvidence**

`id`, `url`, `canonical_url`, `title`, `publisher`, `domain`, `authority_tier`,
`source_class`, `published_at`, `fetched_at`, `content_hash`, `snippet`,
`text_path`, `search_query`, `rank`, `license`, `sensitivity`, `ttl_days`,
`status`, `promotion_candidate_id`.

**Playbook**

`id`, `title`, `persona`, `applies_to`, `steps[]`, `documents[]`, `deadlines[]`,
`penalties[]`, `sources[]`, `status`, `review_due`. Every step carries at least
one approved fact id and a citation.

**EvalItem**

`qid`, `question`, `answer_type`, `gold_answer`, `gold_doc_ids`, `gold_pages`, `difficulty`, `sensitivity`, `notes`.

Identifiers are stable and derived from the source/document identity; chunks keep page and section anchors so a citation can be traced to the original text.

## 7. Storage and runtime

- **Documents and chunks:** local JSONL files under `$SCS_FKB_DATA_ROOT/v2/processed/`; the legacy `processed/` store remains for rollback.
- **Vector index:** LanceDB under `$SCS_FKB_DATA_ROOT/v2/index/`.
- **Keyword index:** local BM25 index under `$SCS_FKB_DATA_ROOT/v2/index/`.
- **Web cache:** `$SCS_FKB_DATA_ROOT/v2/web-cache/`, private, TTL-managed.
- **Manifest:** source and index versions, hashes, counts, model and config hashes.
- **Runs:** commands, model identifiers, metrics and evidence hashes under `$SCS_FKB_RUN_ROOT/`.
- **Runtime:** Python 3.11+ (3.12 recommended for optional P10 dependencies), CPU-only local embedding/reranking, hosted model endpoint, 8 GB RAM, no Docker.
- **No database server:** local files, LanceDB and an in-memory BM25 index are sufficient.

## 8. Quality attributes

| Attribute | Target |
|---|---|
| Citability | Every factual claim has a citation that resolves to a retrieved chunk |
| Reproducibility | The same corpus, index and configuration produce the same retrieval results |
| Data locality | No data, index or run artifact is published |
| Sensitivity | Restricted content never reaches an external model |
| Graceful degradation | Insufficient evidence leads to abstention, not fabrication |
| Observability | Each run records commands, model, index version and evidence hashes |
| Maintainability | Single-purpose modules; no premature framework |

## 9. Security and privacy

- Secrets come from `.env`; `.env` is never committed.
- `restricted` sources stay local; `internal` sources require approval and desensitisation before external use.
- Logs record request metadata, not sensitive source text.
- Public tests and examples use synthetic or public content only.
- The public repository contains no data payloads, indexes, run outputs or state databases.

## 10. Failure modes and degradation

| Failure | Behaviour |
|---|---|
| Source licence or sensitivity unknown | Source is held; not ingested |
| OCR or table extraction fails | Item is quarantined; not silently accepted |
| Index missing or stale | Query returns an explicit error; no answer is fabricated |
| Model endpoint unavailable | Query returns an explicit error or a retrieval-only result |
| Web search unavailable | Canonical-only answer; the response says live checking was unavailable |
| Web evidence outside the allowlist | Result is discarded and the reason is logged |
| Web evidence expired | Evidence is not used; a new fetch is attempted or the answer abstains |
| Evidence insufficient | Answer abstains with a reason |
| Citation does not resolve | Answer is rejected or downgraded; the failure is reported |
| Sensitivity filter blocks evidence | Answer abstains; no restricted content is sent |
| Local memory pressure | Batch size and embedding model size are reduced |

## 11. Interface and downstream integration

- P10-ANS-141 implements a local `/v1` query service and a Web UI; the contract is
  documented in `docs/interface.md` and `configs/interface.yaml`.
- It defines request/response fields, citations, abstention, conflict, web
  evidence, feedback, error codes and API versioning.
- It does not implement data integration, forecast-product storage, multi-tenant
  authentication or the downstream platform. The default bind is localhost; a
  wider bind requires an API key and a decision.

## 12. References

- [Project scope](../PROJECT.md)
- [Project plan](plan.md)
- [RAG standard](rag-standard.md)
- [Evaluation](evaluation.md)
- [Corpus inventory](corpus.md)
- [Data model](data-model.md)
- [Data policy](data-policy.md)
- [Two-plane evidence](adr/0005-two-plane-evidence.md)
- [LlamaIndex/LanceDB/BGE](adr/0006-llamaindex-lancedb-bge.md)
- [Controlled web evidence](adr/0007-controlled-web-evidence.md)
- [Playbooks and terms](adr/0008-playbooks-and-terms.md)
- [Corpus register](../configs/corpus.yaml)
- [Data schema](../configs/schema.yaml)
