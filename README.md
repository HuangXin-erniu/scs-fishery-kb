# South China Sea Nearshore Fishery Knowledge Base (SCS-FKB)
**南海近海渔船作业与渔情知识库（SCS-FKB）**

[English](README.md) | [简体中文](README.zh-CN.md)

[![CI](https://github.com/HuangXin-erniu/scs-fishery-kb/actions/workflows/ci.yml/badge.svg)](https://github.com/HuangXin-erniu/scs-fishery-kb/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey.svg)](LICENSE-docs)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

A retrieval-augmented knowledge base for **fishing vessel operations** and **fishery conditions** in the nearshore **South China Sea**.

The project turns documents, data dictionaries, product descriptions, fishery bulletins, regulations, standards and research reports into a searchable, citable and evaluable domain knowledge base, and provides retrieval-augmented question answering with traceable evidence.

> **中文简介**：本项目把南海近海渔船作业与渔情相关的公开文档、统计口径、法规标准与产品说明，
> 整理成可检索、可引用、可评测的领域知识库，并提供带出处证据的检索增强问答。
> 当前处于**数据准备与语料查找**阶段：先确认南海近海范围、来源权威性和指标覆盖，检索管线暂不实现。
> 仓库不发布任何数据或运行产物；完整中文说明见 [README.zh-CN.md](README.zh-CN.md)。

## Status

**Corpus and data preparation (WP1) complete for this phase; the retrieval pipeline runs only as a local prototype.** Forty-five sources are registered: forty-two acquired and three candidates, all deferred. The acquired set is nine fishery yearbook editions (data years 2017–2025, 838 files — 837 Excel tables and one scanned PDF), six national fishery statistical bulletins (data years 2020–2025), the China Statistical Yearbook 2026, and twenty-six legal and technical documents — one law, ten regulations, four notices, six standard sets (including seventeen SC/T standards held as image-only reference PDFs, 295 pages and the CWP statistical definitions), one operations reference, one port plan and three reference dictionaries. Licence, sensitivity, version and SHA-256 are recorded for every source; the yearbooks are internal, local-use sources. The coverage matrix and the 3,126-row local core CSV (2017–2024 plus a harmonised 2025 sample) stay outside the public tree. Three gaps are documented: no port table for data years 2018–2019, no marine vessel-length table for 2024, and 2025 as a sample. The sufficiency review is accepted: ten of the twenty-four draft questions are answerable, six partial and eight abstention tests. M1 now runs locally as an extractive prototype: the twenty-nine indexed public sources parse into 703 chunks with article, section and page anchors, anchor-level Recall@5 is 8/11 on the eleven questions with gold anchors, BM25 returns evidence packs whose citations resolve, and the evaluation is reported below. Its code is public; the corpus, the processed store and the run reports stay local.

### Corpus at a glance

| Item | Value |
|---|---|
| Registered sources | 45 — 42 acquired, 3 candidates (all deferred) |
| Fishery yearbooks | 9 editions, data years 2017–2025, 838 files |
| National bulletins | 6, data years 2020–2025 |
| China Statistical Yearbook | 2026 edition |
| Legal and technical documents | 26 — 1 law, 10 regulations, 4 notices, 6 standard sets, 1 operations reference, 1 port plan, 3 dictionaries |
| SC/T standards held | 17 (295 pages, image-only reference PDFs) |
| Local core CSV | 3,126 rows, not published |
| Documented gaps | port classes 2018–2019; vessel length 2024; 2025 sampled |
| Sufficiency review | 10 answerable, 6 partial, 8 abstention tests |

This project has no versioned releases: no tags, no GitHub Releases and no semantic versions. `main` is the latest state; cite a commit SHA. Changes are recorded in the [project log](docs/project-log.md).

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
| [Project scope](PROJECT.md) · [中文](PROJECT.zh-CN.md) | Objectives, scope, non-goals and data policy |
| [Architecture](docs/architecture.md) | Layers, components, data flow, data contracts and runtime |
| [Project plan](docs/plan.md) | Work packages, milestones, roles, quality gates and risks |
| [Evaluation](docs/evaluation.md) | Question set, metrics, protocol, targets and reporting |
| [Corpus inventory](docs/corpus.md) | Acquired and candidate sources, licences, sensitivity and priorities |
| [Project log](docs/project-log.md) | Dated record of material project changes |
| [Governance](GOVERNANCE.md) | Roles, decisions, version policy and boundaries |
| [Glossary](docs/glossary.md) | Bilingual terminology for fishery and retrieval concepts |
| [Architecture decisions](docs/adr/README.md) | Dated records of material project decisions |
| [Style guide](docs/style-guide.md) | Language, links, citations and commit conventions |

## Repository layout

```text
scs-fishery-kb/
├── README.md / README.zh-CN.md
├── PROJECT.md / PROJECT.zh-CN.md
├── GOVERNANCE.md                roles, decisions and boundaries
├── LICENSE / LICENSE-docs       code Apache-2.0; docs CC BY 4.0
├── CITATION.cff
├── .github/                     community files, CI, issue and PR templates
├── configs/                     corpus register and schema
├── docs/                        architecture, plan, evaluation, policy, glossary, ADRs
├── scripts/                     public-tree validation
└── tests/                       config and public-tree tests
```

Data and run artifacts are local-only and never enter the published tree.

## Quick start

```sh
git clone https://github.com/HuangXin-erniu/scs-fishery-kb.git
cd scs-fishery-kb

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

make check
```

`make check` runs lint, format check, tests and the public-tree validation. `requirements.txt` contains only the readers used for the register (PyYAML, openpyxl, xlrd); the pipeline itself uses the standard library.

The pipeline reads sources from `SCS_FKB_DATA_ROOT` and writes the processed store there; no data and no index enter the repository:

```sh
export SCS_FKB_DATA_ROOT=/path/to/local/data
make ingest   # parse the three configured documents and build the local chunks
make eval     # document-level Recall@5, abstention and citation metrics
```

`make ingest` and `make eval` need the local data root; CI runs `make check` only, so the public tree stays data-free.

## Data and artifacts

- Data and run artifacts live outside the repository and are never committed.
- `SCS_FKB_DATA_ROOT` and `SCS_FKB_RUN_ROOT` point to the local data and run roots; see `.env.example`.
- Licences and sensitivity are recorded per source in `configs/corpus.yaml`.
- Sources with `license: unknown` or `sensitivity: unknown` are held and must not be ingested.
- `restricted` sources must stay local and must never be sent to an external model API.
- The public repository contains no data, no indexes and no run outputs.

See [docs/data-policy.md](docs/data-policy.md) for details.

## Roadmap

| Milestone | Deliverable | Status |
|---|---|---|
| M0 | Framework: scope, architecture, plan, evaluation, corpus register, tooling | done |
| M1 | Minimal pipeline: parse, chunk, index, retrieve, answer with citations | next: owner decision pending |
| M2 | Retrieval baseline: BM25 / dense / hybrid comparison | planned |
| M3 | Evaluation report and service prototype | planned |
| M4 | `/v1` query interface contract for downstream integration | planned |

Milestones describe work stages, not releases. The corpus sufficiency review was accepted on 2026-11-01, so the start of M1 is an owner decision rather than a corpus condition. The M4 contract is limited to `docs/interface.md` and `configs/interface.yaml` when it is added; it does not include data integration.

## Citation

If you use this project, please cite it using [CITATION.cff](CITATION.cff).

## License

- Code: [Apache License 2.0](LICENSE).
- Documentation: [Creative Commons Attribution 4.0 International](LICENSE-docs).
- Data: not distributed with this repository; see [docs/data-policy.md](docs/data-policy.md).

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md), [CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md), [SECURITY.md](.github/SECURITY.md) and [GOVERNANCE.md](GOVERNANCE.md).
