# South China Sea Nearshore Fishery Knowledge Base (SCS-FKB)

[![CI](https://github.com/HuangXin-erniu/scs-fishery-kb/actions/workflows/ci.yml/badge.svg)](https://github.com/HuangXin-erniu/scs-fishery-kb/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey.svg)](LICENSE-docs)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

A retrieval-augmented knowledge base for **fishing vessel operations** and **fishery conditions** in the nearshore **South China Sea**.

The project turns documents, data dictionaries, product descriptions, fishery bulletins, regulations, standards and research reports into a searchable, citable and evaluable domain knowledge base, and provides retrieval-augmented question answering with traceable evidence.

## Status

**Early-stage public framework.** The architecture, work packages and evaluation protocol are documented. The retrieval pipeline and service code are planned but not implemented yet.

No versioned releases are published. Project changes are recorded in the [project log](docs/project-log.md).

**No data or run artifacts are published in this repository.** See [docs/data-policy.md](docs/data-policy.md).

## Scope

**In scope**

- Knowledge-layer corpus governance: sources, licences, sensitivity, metadata, versions and hashes.
- Document parsing, structure-aware chunking and table/indicator extraction.
- Hybrid retrieval (BM25 + dense embeddings) with metadata filters and optional reranking.
- Retrieval-augmented answers with citations, abstention and evaluation.
- A `/v1` query interface contract for downstream platform integration (contract only; no data integration).

**Out of scope**

- Training or serving fishery-forecasting models.
- Publishing raw environmental grids, forecast products, or full AIS/VMS tracks.
- Production multi-tenant platform, authentication or monitoring.
- Data integration with downstream platforms; that work is handled separately.

## Framework and plan

| Document | Purpose |
|---|---|
| [Project scope](PROJECT.md) | Objectives, scope, non-goals and data policy |
| [Architecture](docs/architecture.md) | Layers, components, data flow, data contracts and runtime |
| [Project plan](docs/plan.md) | Work packages, milestones, roles, quality gates and risks |
| [Evaluation](docs/evaluation.md) | Question set, metrics, protocol, targets and reporting |
| [Corpus inventory](docs/corpus.md) | Candidate sources, licences, sensitivity and acquisition priorities |
| [Project log](docs/project-log.md) | Dated record of material project changes |

## Repository layout

```text
scs-fishery-kb/
├── README.md / README.zh-CN.md
├── PROJECT.md                  scope, objectives and non-goals
├── LICENSE / LICENSE-docs      code Apache-2.0; docs CC BY 4.0
├── CITATION.cff
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── .github/                    CI, issue and PR templates
├── configs/                    corpus register and schema
├── data/                       no payloads; policy README only
├── docs/                       architecture, plan, evaluation, project log, corpus, questions, data policy
├── scripts/                    public-tree validation
└── tests/                      config and public-tree tests
```

`data/` and `runs/` are local-only. No payloads, indexes, run logs or state databases are committed.

## Quick start

```sh
git clone https://github.com/HuangXin-erniu/scs-fishery-kb.git
cd scs-fishery-kb

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

make validate
make lint
make test
```

The runtime dependencies in `requirements.txt` are installed when the retrieval code lands. The current repository contains documentation, configuration and validation tooling only.

## Data and artifacts

- `data/` holds local source files and indexes; it is gitignored except for `data/README.md`.
- `runs/` holds local run artifacts; it is gitignored entirely.
- Licences and sensitivity are recorded per source in `configs/corpus.yaml`.
- Sources with `license: unknown` or `sensitivity: unknown` are held and must not be ingested.
- `restricted` sources must stay local and must never be sent to an external model API.
- The public repository contains no data, no indexes and no run outputs.

See [docs/data-policy.md](docs/data-policy.md) for details.

## Roadmap

| Milestone | Deliverable | Status |
|---|---|---|
| M0 | Framework: scope, architecture, plan, evaluation, corpus register, tooling | current |
| M1 | Minimal pipeline: parse, chunk, index, retrieve, answer with citations | planned |
| M2 | Retrieval baseline: BM25 / dense / hybrid comparison | planned |
| M3 | Evaluation report and service prototype | planned |
| M4 | `/v1` query interface contract for downstream integration | planned |

Milestones describe work stages, not releases. The M4 contract is limited to `docs/interface.md` and `configs/interface.yaml` when it is added; it does not include data integration.

## Citation

If you use this project, please cite it using [CITATION.cff](CITATION.cff).

## License

- Code: [Apache License 2.0](LICENSE).
- Documentation: [Creative Commons Attribution 4.0 International](LICENSE-docs).
- Data: not distributed with this repository; see [docs/data-policy.md](docs/data-policy.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md).

中文说明见 [README.zh-CN.md](README.zh-CN.md).
