# Project Scope: South China Sea Nearshore Fishery Knowledge Base (SCS-FKB)

## 1. Identity

| Item | Value |
|---|---|
| Project | South China Sea Nearshore Fishery Knowledge Base (SCS-FKB) |
| Full title | South China Sea Nearshore Fishery Knowledge Base (SCS-FKB): Construction and Retrieval-Augmented Generation Methods |
| Status | Early-stage public framework; architecture, plan and evaluation are documented; implementation is planned |
| Domain | Nearshore fisheries in the South China Sea: fishing vessel operations and fishery conditions |
| Method | Retrieval-augmented generation with citations, abstention and evaluation |

The project has no versioned releases: no tags, no GitHub Releases and no semantic versions. `main` is the latest state; material changes are recorded by date in the [project log](docs/project-log.md).

## 2. Background

Knowledge about nearshore fishing vessel operations and fishery conditions is scattered across statistical yearbooks, logbook specifications, vessel and voyage data dictionaries, ocean-product descriptions, fishery bulletins, regulations, standards, research papers and project reports. Formats, terminology and statistical definitions differ across sources. A direct keyword search or an unconstrained language-model answer can be fast but difficult to verify.

SCS-FKB addresses this by treating the **knowledge layer** as a governed corpus: every source is registered with its licence, sensitivity, version and hash; every answer must point to evidence; and every retrieval or answer quality claim is measured against a documented evaluation set.

The project is developed within a broader research programme on nearshore fishery forecasting and knowledge services. It focuses on the knowledge base and retrieval-augmented generation. Forecast models, raw environmental data and platform integration are separate workstreams.

## 3. Objectives

1. Build a governed corpus of nearshore South China Sea fishing-vessel and fishery-condition knowledge, with clear source, licence, sensitivity and version metadata.
2. Organise documents into citable knowledge units: page, section, table and indicator level.
3. Implement hybrid retrieval and retrieval-augmented answers with traceable citations and explicit abstention.
4. Establish a reproducible evaluation set and baseline for retrieval, citation and answer quality.
5. Publish a `/v1` query interface contract for downstream platform integration, without implementing that integration.

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

## 5. Framework and plan

| Document | Purpose |
|---|---|
| [Architecture](docs/architecture.md) | Layers, components, data flow, data contracts, runtime and security |
| [Project plan](docs/plan.md) | Work packages, milestones, dependencies, roles, quality gates and risks |
| [Evaluation](docs/evaluation.md) | Question set, metrics, protocol, targets and reporting |
| [Project log](docs/project-log.md) | Dated record of material project changes |
| [Governance](GOVERNANCE.md) | Roles, decisions, version policy and boundaries |
| [Glossary](docs/glossary.md) | Bilingual terminology for fishery and retrieval concepts |
| [Architecture decisions](docs/adr/README.md) | Dated records of material project decisions |
| [Style guide](docs/style-guide.md) | Language, links, citations and commit conventions |

The framework defines the ingestion, retrieval, evidence, evaluation and service layers. The plan defines WP0–WP6 and milestones M0–M4. The evaluation document defines how retrieval, citation and answer quality are measured.

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

The full component and contract description is in [architecture.md](docs/architecture.md).

## 7. Roadmap

| Milestone | Deliverable | Exit condition |
|---|---|---|
| M0 | Framework and public baseline | Scope, architecture, plan, evaluation, corpus register and CI are published |
| M1 | Minimal pipeline on two or three documents | Answers with citations |
| M2 | Retrieval baseline (BM25 / dense / hybrid) | Retrieval report |
| M3 | Evaluation report and service prototype | Demonstrates end-to-end use |
| M4 | `/v1` query interface contract | Contract reviewed; no data integration |

Milestones describe work stages, not releases. Details are in [plan.md](docs/plan.md).

## 8. Data policy

- No data is distributed with this repository.
- Every source carries `license` and `sensitivity`; `unknown` values are held and must not be ingested.
- `restricted` sources stay local and are never sent to an external model API.
- Vessel-tracking data is limited to data dictionaries and desensitised sample descriptions; full tracks are out of scope.
- Personal or vessel-identifying information is aggregated or anonymised.
- `data/` and `runs/` are local-only and gitignored.
- Details: [data-policy.md](docs/data-policy.md).

## 9. Interface contract

- The downstream interface is planned as a `/v1` query contract.
- It will be limited to `docs/interface.md` and `configs/interface.yaml`.
- It will define request/response fields, citation shape, abstention semantics, error codes and API versioning.
- It will not implement data integration, forecast-product storage or platform authentication.

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Source licences or sensitivity unclear | Cannot ingest or publish | Register every source; `unknown` is held; `restricted` stays local |
| Scanned documents or complex tables | Extraction errors | Text-layer PDFs first; OCR optional; low-quality items quarantined; human spot checks |
| Evaluation set bias | Metrics look good but do not reflect use | Real user questions; expert review; held-out set; human review authoritative |
| Scope expansion | Becomes a forecasting or platform project | Scope and non-goals in this document; changes go through a decision |
| Local resource limits (8 GB) | Large local models or parallel jobs are impractical | Hosted model endpoint; small local embeddings; batch processing; one active task |
| Interface drift | Downstream rework | `/v1` contract; additive fields; index version traceability |

Full risk and quality-gate detail is in [plan.md](docs/plan.md).

## 11. Non-goals

- Fishery-forecasting model training, inference or forecast products.
- Raw environmental grids, reanalysis data or full AIS/VMS tracks.
- A production multi-tenant platform.
- Data integration with downstream platforms.
- Publishing restricted or unlicensed data.
- Modifying the separate research programme's repositories.

## 12. Versioning and releases

- The project uses no semantic versions, Git tags or GitHub Releases.
- `main` is the only supported line; a commit SHA identifies a state.
- Material changes are recorded by date in the [project log](docs/project-log.md).
- Milestones M0–M4 are work stages, not versions.
- The repository is expected to have no tags; CI and the public-tree check reject tags.

## 13. References

- [Architecture](docs/architecture.md)
- [Project plan](docs/plan.md)
- [Evaluation](docs/evaluation.md)
- [Project log](docs/project-log.md)
- [Corpus register](configs/corpus.yaml)
- [Data schema](configs/schema.yaml)
- [Corpus inventory](docs/corpus.md)
- [Evaluation questions](docs/questions.md)
- [Data policy](docs/data-policy.md)
- [Citation metadata](CITATION.cff)
- [Governance](GOVERNANCE.md)
- [Glossary](docs/glossary.md)
- [Architecture decisions](docs/adr/README.md)
- [Style guide](docs/style-guide.md)
