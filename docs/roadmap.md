# Roadmap

## M0 — Public baseline (`v0.1.0-alpha`)

- Project scope, objectives and non-goals.
- Governed source register with seven categories and fourteen candidates.
- Twenty-four draft evaluation questions.
- Data policy, method outline and documentation index.
- Public-tree validation, configuration tests and CI.
- Licences, citation metadata and community files.

Exit condition: `v0.1.0-alpha` is published and CI passes.

## M1 — Minimal pipeline

- Parse, chunk and index two or three public documents.
- Build BM25 and dense retrieval.
- Answer with page/section citations.
- Add abstention when evidence is insufficient.

Exit condition: a documented end-to-end demonstration on the first public corpus.

## M2 — Retrieval baseline

- Compare BM25-only, dense-only and hybrid retrieval.
- Measure Recall@k, MRR and Hit@k.
- Record query rewriting and metadata-filter effects.
- Identify failure cases and corpus gaps.

Exit condition: a reproducible retrieval report with a reviewed question subset.

## M3 — Evaluation and service prototype

- Expand the reviewed question set.
- Measure citation precision, coverage and answer correctness.
- Add a command-line and HTTP query surface.
- Produce an evaluation report and error analysis.

Exit condition: an end-to-end prototype and a baseline report.

## M4 — Interface contract

- Define `docs/interface.md` and `configs/interface.yaml`.
- Specify request/response fields, citations, abstention, error codes and versioning.
- Review the contract with the downstream integration owner.

Exit condition: the contract is reviewed and published.

M4 defines the contract only. It does not implement data integration, forecast-product storage, authentication or the downstream platform.

## Out of scope for all milestones

- Fishery-forecasting model training or products.
- Raw environmental grids, reanalysis data or full AIS/VMS tracks.
- Production multi-tenant deployment.
- Publishing restricted or unlicensed data.

See [PROJECT.md](../PROJECT.md) for the full scope and [data-policy.md](data-policy.md) for the data boundary.
