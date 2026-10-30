# Project Plan

- Status: active plan; the project is at an early-stage public framework.
- No versioned releases are published. Milestones describe work stages, not release numbers.
- Architecture: [architecture.md](architecture.md); evaluation: [evaluation.md](evaluation.md); scope: [../PROJECT.md](../PROJECT.md).

## 1. Purpose

This plan turns the project scope into work packages, deliverables, milestones and acceptance criteria. It is the reference for what is built, in what order, and how completion is judged.

## 2. Scope summary

The project builds a governed knowledge-layer corpus of nearshore South China Sea fishing-vessel and fishery-condition material, a hybrid retrieval pipeline, evidence-grounded answers with citations and abstention, and a reproducible evaluation. It does not train forecast models, publish raw environmental data or full vessel tracks, or integrate downstream platform data.

Detailed scope and non-goals are in [../PROJECT.md](../PROJECT.md). The architecture is in [architecture.md](architecture.md).

## 3. Work packages

| WP | Name | Deliverables | Acceptance |
|---|---|---|---|
| WP0 | Framework and governance | Scope, architecture, plan, evaluation, corpus register, questions, public tooling and CI | Documents reviewed; CI passes |
| WP1 | Corpus acquisition and registration | Two or three P1 public documents; licence, sensitivity, version and hash recorded | No unknown source ingested; acquisition path documented |
| WP2 | Ingestion and knowledge organisation | Parser, chunker, table/indicator extraction; processed records and manifest | Page/section/table anchors present; manifest reproducible |
| WP3 | Retrieval | BM25, dense retrieval, fusion, metadata/sensitivity filtering; retrieval report | Retrieval baseline measured on a reviewed subset |
| WP4 | Answer generation and evidence | Evidence-only prompt, citation validation, abstention | No fabricated citation; out-of-scope refusal works |
| WP5 | Evaluation | Reviewed question set; baselines; error analysis; evaluation report | Metrics and limitations reported |
| WP6 | Service and interface | CLI/HTTP query surface; `/v1` interface contract (`docs/interface.md`, `configs/interface.yaml`) | Contract reviewed; no data integration implemented |

WP0 is the current stage. WP1 must start with owner-confirmed public documents; WP2–WP5 build on that corpus.

## 4. Milestones

| Milestone | Content | Exit condition |
|---|---|---|
| M0 | Framework and public baseline | Scope, architecture, plan, evaluation, corpus register, questions and CI are published |
| M1 | Minimal pipeline | Two or three documents are parsed, indexed and answerable with citations |
| M2 | Retrieval baseline | BM25, dense and hybrid retrieval are compared on a reviewed subset |
| M3 | Evaluation and service prototype | Citation/answer metrics and an end-to-end CLI/HTTP demonstration are reported |
| M4 | Interface contract | The `/v1` contract is reviewed; no data integration is included |

Milestones do not create releases or tags. Completion is judged by the exit condition and the quality gates below.

## 5. Dependencies and sequence

```text
WP0 framework
  → WP1 corpus
    → WP2 ingestion
      → WP3 retrieval
        → WP4 answers
          → WP5 evaluation
            → WP6 service + interface contract
```

- WP1 depends on source owners and licence confirmation.
- WP2 depends on at least two public documents.
- WP3 and WP4 can iterate together after the first index exists.
- WP6 depends on a stable query path; the contract is defined after WP3/WP4 are demonstrable.

## 6. Roles

| Role | Responsibility |
|---|---|
| Project owner / decision-maker | Scope, priorities, decisions, review and acceptance |
| Maintainer / executor | Implementation, tests, documentation and evidence |
| Domain expert | Real questions, definitions, gold answers and answer review |
| Data owner | Source access, licence, sensitivity and permitted use |
| Downstream interface owner | Review of the `/v1` contract and integration boundary |

The project owner approves scope changes. The maintainer records evidence for every deliverable. Domain experts review the question set and answer quality. Data owners confirm source terms.

## 7. Schedule

A six-week working schedule is suggested; it can be compressed or extended.

| Week | Focus | Output |
|---|---|---|
| 1 | Framework and corpus discovery | Reviewed scope/architecture/plan; P1 source list |
| 2–3 | Ingestion and minimal retrieval | Processed corpus; first citations |
| 4 | Retrieval baseline | BM25/dense/hybrid comparison |
| 5 | Evaluation and service | Metrics report; CLI/HTTP prototype |
| 6 | Contract and review | `/v1` contract; final review |

Dates are not commitments. Milestone exit conditions and quality gates take precedence.

## 8. Quality gates

1. **Source gate:** licence and sensitivity known; unknown sources held; restricted sources local-only.
2. **Public-tree gate:** `scripts/check_public_tree.py` passes; no data, run artifacts, secrets or absolute paths.
3. **Citation gate:** every factual claim has a citation that resolves to a retrieved chunk.
4. **Evaluation gate:** reviewed questions, baseline comparison, error analysis and human review.
5. **CI gate:** `ruff check`, `ruff format --check`, `pytest` and the public-tree check pass.

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Source licences or sensitivity unclear | Cannot ingest or publish | Register every source; hold unknown values; keep restricted sources local |
| Scanned documents or complex tables | Extraction errors | Text-layer PDFs first; OCR optional; quarantine low-quality items; human spot checks |
| Evaluation set bias | Metrics look good but do not reflect use | Real questions; expert review; held-out set; human review authoritative |
| Scope expansion | Becomes a forecasting or platform project | Scope and non-goals in PROJECT.md; changes go through the owner |
| Local resource limits (8 GB) | Large models or parallel jobs are impractical | Hosted model endpoint; small local embeddings; batch processing; one active task |
| Interface drift | Downstream rework | `/v1` contract; additive fields; index version traceability |
| Missing corpus | The minimal pipeline cannot start | Owner provides two or three P1 public documents first |

## 10. Change control

- Scope changes, new data classes and new external dependencies require a project decision.
- The public tree must remain free of data, run artifacts, secrets and internal identifiers.
- A change that affects the `/v1` contract requires review with the downstream interface owner.
- No release or tag is created as part of this plan.

## 11. Out of scope

- Fishery-forecasting model training, inference or products.
- Raw environmental grids, reanalysis data or full AIS/VMS tracks.
- A production multi-tenant platform.
- Downstream data integration.
- Publishing restricted or unlicensed data.

## 12. References

- [Project scope](../PROJECT.md)
- [Architecture](architecture.md)
- [Evaluation](evaluation.md)
- [Corpus inventory](corpus.md)
- [Evaluation questions](questions.md)
- [Data policy](data-policy.md)
- [Corpus register](../configs/corpus.yaml)
- [Data schema](../configs/schema.yaml)
