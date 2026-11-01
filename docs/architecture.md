# Architecture

> **中文摘要**：本文件描述 SCS-FKB 的分层架构、组件、数据流、数据契约与运行方式。
> 当前框架已定义，M1 抽取式原型在本机运行；数据与运行产物只留在本机，不进入公开仓库。
> 所有回答必须基于检索证据并带可核验引用；`restricted` 来源不得发送到外部模型 API。

- Status: framework documented; the M1 extractive prototype runs locally over three documents. Retrieval beyond BM25, generation and the service surface are still deferred.
- Scope: knowledge-layer corpus, retrieval, evidence-grounded answers and evaluation.
- Non-goals: forecast-model training, raw environmental data, full vessel tracks and downstream data integration.

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
6. **No premature platform.** The project builds a local prototype and a contract; it does not build a production platform.

## 3. Logical architecture

| Layer | Component | Responsibility |
|---|---|---|
| Interface | CLI / HTTP | `ingest`, `retrieve`, `ask`, `eval`; `/v1/query` for downstream use |
| Orchestration | Pipeline runner | Ingestion pipeline, query pipeline and evaluation runner |
| Retrieval | Retriever | Query rewriting, BM25, dense retrieval, fusion, metadata filtering, optional reranking |
| Generation | Answer engine | Prompt construction, model client, citation validation, abstention |
| Knowledge | Knowledge store | Documents, chunks, vector index, BM25 index and manifest |
| Data | Ingestion | Parsing, OCR, chunking, table/indicator extraction, hashing and deduplication |
| Governance | Source register | Licence, sensitivity, version, hash and acquisition status |
| Evaluation | Evaluation runner | Question set, retrieval/citation/answer metrics and reports |

## 4. Components and module map

```text
src/scs_fkb/parsers/   html.py, docx.py, ofd.py — format adapters with page and line anchors
src/scs_fkb/patterns.py article, section and chapter expressions
src/scs_fkb/chunking.py page-aware article, section and fallback chunking
src/scs_fkb/bm25.py     character-bigram BM25 with a sensitivity filter
src/scs_fkb/answer.py   extractive evidence pack, citation validation and abstention
src/scs_fkb/evaluate.py document-level retrieval, abstention and citation metrics
src/scs_fkb/store.py    processed documents, chunks and manifest
src/scs_fkb/cli.py      ingest, retrieve, ask and eval
configs/pipeline.yaml   documents, chunking, retrieval and answer parameters
local data root         raw and processed data (outside the repository)
tests/                  configuration, parser, pipeline and public-tree tests
```

Each module exposes a small callable surface rather than a framework. Shared code is extracted only when a second module needs it. M1 is deterministic: it makes no model call, builds no embedding and needs no network access. Citations carry a page anchor for the paginated OFD and PDF sources and an article or section anchor for the HTML, DOCX and DOC sources. The ranker is BM25 over character bigrams with an optional title boost, which multiplies a chunk score by 1 + title_boost × the share of query tokens present in the document title. The evaluation compares the top five chunks against gold anchors in `configs/eval.yaml`: a document plus a section prefix, or a document plus a page.

## 5. Data flow

```text
<data_root>/raw
  → source register (licence / sensitivity / version / hash)
  → parsing and OCR
  → structure-aware chunking and table/indicator extraction
  → <data_root>/processed (documents, chunks, metadata)
  → local embeddings + BM25 index
  → query rewriting
  → hybrid retrieval
  → metadata and sensitivity filtering
  → evidence-only answer with citations / abstention
  → evaluation and run report
```

The ingestion path is offline and repeatable. The query path is read-only with respect to the corpus; it reads the current index and writes only a run report.

## 6. Data contracts

The machine-readable schema is [configs/schema.yaml](../configs/schema.yaml). The main records are:

**SourceRecord**

`id`, `category`, `title`, `title_zh`, `publisher`, `year`, `type`, `format`, `location`, `license`, `sensitivity`, `status`, `priority`, `volume`, `update_freq`, `hash`, `acquisition`, `notes`.

**Document**

`doc_id`, `source_id`, `title`, `title_zh`, `publisher`, `year`, `doc_type`, `sensitivity`, `language`, `page_count`, `file_hash`.

**Chunk**

`chunk_id`, `doc_id`, `page`, `section`, `table_id`, `text`, `token_count`, `char_start`, `char_end`.

**Citation**

`doc_id`, `title`, `page`, `section`, `snippet`, `score`.

**Answer**

`answer`, `citations`, `abstained`, `reason`, `index_version`, `model`.

**EvalItem**

`qid`, `question`, `answer_type`, `gold_answer`, `gold_doc_ids`, `gold_pages`, `difficulty`, `sensitivity`, `notes`.

Identifiers are stable and derived from the source/document identity; chunks keep page and section anchors so a citation can be traced to the original text.

## 7. Storage and runtime

- **Documents and chunks:** local JSONL files under `$SCS_FKB_DATA_ROOT/processed/`.
- **Vector index:** embedded vector store under `$SCS_FKB_DATA_ROOT/index/`.
- **Keyword index:** local BM25 index under `$SCS_FKB_DATA_ROOT/index/`.
- **Manifest:** source and index versions, hashes and counts.
- **Runs:** commands, model identifiers, metrics and evidence hashes under `$SCS_FKB_RUN_ROOT/`.
- **Runtime:** Python 3.11+, CPU-only local embedding, hosted model endpoint.
- **No database server:** local files and embedded indexes are sufficient for the prototype.

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
| Evidence insufficient | Answer abstains with a reason |
| Citation does not resolve | Answer is rejected or downgraded; the failure is reported |
| Sensitivity filter blocks evidence | Answer abstains; no restricted content is sent |
| Local memory pressure | Batch size and embedding model size are reduced |

## 11. Interface and downstream integration

- The downstream interface is planned as a `/v1` query contract.
- It will be limited to `docs/interface.md` and `configs/interface.yaml` when added.
- It will define request/response fields, citations, abstention, error codes and API versioning.
- It will not implement data integration, forecast-product storage, authentication or the downstream platform.

## 12. References

- [Project scope](../PROJECT.md)
- [Project plan](plan.md)
- [Evaluation](evaluation.md)
- [Corpus inventory](corpus.md)
- [Data policy](data-policy.md)
- [Corpus register](../configs/corpus.yaml)
- [Data schema](../configs/schema.yaml)
