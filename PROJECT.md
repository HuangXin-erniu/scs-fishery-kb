# Project Scope: South China Sea Nearshore Fishery Knowledge Base (SCS-FKB)

## 1. Identity

| Item | Value |
|---|---|
| Project | South China Sea Nearshore Fishery Knowledge Base (SCS-FKB) |
| Full title | South China Sea Nearshore Fishery Knowledge Base (SCS-FKB): Construction and Retrieval-Augmented Generation Methods |
| Version | `0.1.0-alpha` |
| Status | Public baseline: scope, corpus register, evaluation questions, documentation and tooling |
| Domain | Nearshore fisheries in the South China Sea: fishing vessel operations and fishery conditions |
| Method | Retrieval-augmented generation with citations, abstention and evaluation |

## 2. Background

Knowledge about nearshore fishing vessel operations and fishery conditions is scattered across statistical yearbooks, logbook specifications, vessel and voyage data dictionaries, ocean-product descriptions, fishery bulletins, regulations, standards, research papers and project reports. Formats, terminology and statistical definitions differ across sources. A direct keyword search or an unconstrained language-model answer can be fast but difficult to verify.

SCS-FKB addresses this by treating the **knowledge layer** as a governed corpus: every source is registered with its licence, sensitivity, version and hash; every answer must point to evidence; and every retrieval or answer quality claim is measured against a documented evaluation set.

The project is developed within a broader research programme on nearshore fishery forecasting and knowledge services. It focuses on the knowledge base and retrieval-augmented generation. Forecast models, raw environmental data and platform integration are separate workstreams.

## 3. Objectives

1. Build a governed corpus of nearshore South China Sea fishing-vessel and fishery-condition knowledge, with clear source, licence, sensitivity and version metadata.
2. Organise documents into citable knowledge units: page, section, table and indicator level.
3. Implement hybrid retrieval and retrieval-augmented answers with traceable citations and explicit abstention.
4. Establish a reproducible evaluation set and baseline for retrieval, citation and answer quality.
5. Publish a versioned query interface contract for downstream platform integration, without implementing that integration.

## 4. Scope

### 4.1 In scope

- Fishing-vessel operations and catch statistics: yearbooks, logbook specifications, operation types and catch indicators.
- Vessel/voyage data dictionaries and desensitised sample descriptions; not full tracks.
- Ocean and fishery product descriptions: variables, units, spatial/temporal resolution, indicator tables and metadata.
- Fishery bulletins and historical fishing-ground/season records in public form.
- Fisheries laws, regulations, standards and operational norms.
- Public papers, project reports and technical reports.
- Data dictionaries, metric definitions and metadata standards.

### 4.2 Out of scope

- Training or serving fishery-forecasting models.
- Publishing raw environmental grids, reanalysis data, forecast rasters or products.
- Publishing full AIS/VMS tracks or personally identifying vessel information.
- Production multi-tenant deployment, authentication, monitoring or high availability.
- Data integration with downstream platforms; only the interface contract is in scope.

## 5. Research content

1. **Corpus governance.** Source register, licence and sensitivity classification, metadata, versioning and hashing.
2. **Knowledge organisation.** Document parsing, OCR where needed, structure-aware chunking, table and indicator extraction, citation anchors.
3. **Retrieval.** BM25 and dense retrieval, metadata filtering, reciprocal-rank fusion, optional reranking.
4. **Generation and evidence.** Evidence-only answering, citation format, citation validation, abstention when evidence is insufficient.
5. **Evaluation.** A reviewed question set, retrieval/citation/answer metrics, baselines and error analysis.
6. **Service and interface.** A command-line and HTTP query surface, plus a versioned contract for downstream integration.

## 6. Technical approach

```text
local data/raw
  → source register (licence / sensitivity / version / hash)
  → parsing and OCR
  → structure-aware chunking and indicator extraction
  → local embeddings + BM25 index
  → query rewriting and hybrid retrieval
  → metadata filtering and optional reranking
  → evidence-only answer with citations / abstention
  → evaluation and reporting
```

- Parsing: PDF text layer first; Word, Excel and HTML supported; OCR for scanned pages.
- Chunking: section-aware, 512–800 tokens with 10–15% overlap; page/section/table anchors retained.
- Index: embedded vector store plus a BM25 index; metadata filters applied before retrieval.
- Generation: an OpenAI-compatible model endpoint; the model receives only retrieved evidence.
- Citation: `[doc_id p.page]` or `[doc_id §section]`; citations are checked against retrieved chunks.
- Abstention: insufficient evidence, out-of-scope questions or disallowed sensitivity produce an explicit refusal.
- Data locality: no data payloads, indexes or run artifacts are committed; `data/` and `runs/` are local-only.

## 7. Evaluation

- Retrieval: Recall@k, MRR, Hit@k.
- Citation: citation precision, citation coverage, invalid-citation rate.
- Answer: correctness, faithfulness and completeness on a reviewed question set.
- Abstention: out-of-scope refusal accuracy and false-refusal rate.
- Performance: retrieval latency, end-to-end latency, index build time and memory peak.
- Baselines: BM25-only, dense-only and hybrid retrieval.
- Human review is authoritative for answer correctness; automated metrics are supporting evidence.

## 8. Roadmap

| Milestone | Deliverable | Exit condition |
|---|---|---|
| M0 | Public baseline: scope, corpus register, questions, tooling | `v0.1.0-alpha` released |
| M1 | Minimal pipeline on 20–30 documents | Answers with citations |
| M2 | Retrieval baseline (BM25 / dense / hybrid) | Retrieval report |
| M3 | Evaluation report and service prototype | Demonstrates end-to-end use |
| M4 | Versioned query interface contract | Contract reviewed; no data integration |

## 9. Data policy

- No data is distributed with this repository.
- Every source carries `license` and `sensitivity`; `unknown` values are held and must not be ingested.
- `restricted` sources stay local and are never sent to an external model API.
- Vessel-tracking data is limited to data dictionaries and desensitised sample descriptions; full tracks are out of scope.
- Personal or vessel-identifying information is aggregated or anonymised.
- `data/` and `runs/` are local-only and gitignored.
- Details: [data-policy.md](docs/data-policy.md).

## 10. Interface contract

- The downstream interface is planned for M4.
- It will be limited to `docs/interface.md` and `configs/interface.yaml`.
- It will define request/response fields, citation shape, abstention semantics, error codes and versioning.
- It will not implement data integration, forecast-product storage or platform authentication.

## 11. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Source licences or sensitivity unclear | Cannot ingest or publish | Register every source; `unknown` is held; `restricted` stays local |
| Scanned documents or complex tables | Extraction errors | Text-layer PDFs first; OCR optional; low-quality items quarantined; human spot checks |
| Evaluation set bias | Metrics look good but do not reflect use | Real user questions; expert review; held-out set; human review authoritative |
| Scope expansion | Becomes a forecasting or platform project | Scope and non-goals in this document; changes go through a decision |
| Local resource limits (8 GB) | Large local models or parallel jobs are impractical | Hosted model endpoint; small local embeddings; batch processing; one active task |
| Interface drift | Downstream rework | Versioned contract; additive fields; `index_version` traceability |

## 12. Non-goals

- Fishery-forecasting model training, inference or forecast products.
- Raw environmental grids, reanalysis data or full AIS/VMS tracks.
- A production multi-tenant platform.
- Data integration with downstream platforms.
- Publishing restricted or unlicensed data.
- Modifying the separate research programme's repositories.

## 13. References

- [Corpus register](configs/corpus.yaml)
- [Data schema](configs/schema.yaml)
- [Corpus inventory](docs/corpus.md)
- [Evaluation questions](docs/questions.md)
- [Method](docs/method.md)
- [Data policy](docs/data-policy.md)
- [Roadmap](docs/roadmap.md)
- [Citation metadata](CITATION.cff)
