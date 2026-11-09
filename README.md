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

**Corpus and retrieval prototype (WP2) complete for this phase; evaluation is in progress on a draft question set.** Sixty-three sources are registered: sixty-three acquired and no candidates. The set is one law, twenty regulations, twelve notices, seventeen standards, ten statistical yearbooks (nine fishery yearbook editions for data years 2017–2025 and the China Statistical Yearbook 2026), two data dictionaries and one operations reference. Licence, sensitivity, version and SHA-256 are recorded for every source; the yearbooks are internal, local-use sources. The coverage matrix and the 3,126-row local core CSV (2017–2024 plus a harmonised 2025 sample) stay outside the public tree. Three gaps are documented: no port table for data years 2018–2019, no marine vessel-length table for 2024, and 2025 as a sample. The twenty-eight indexed public sources parse into 785 chunks with section and page anchors; the hybrid BM25 plus dense configuration reaches anchor-level Recall@5 of 11/11 (MRR 0.56) on the eleven questions with gold anchors, with abstention 3/4, two false refusals, citation resolution 1.00 and P95 19 ms. The CWP definition channel answers Q-E05 and Q-M04 (2/2), the local statistics channel answers Q-E06 and Q-M05 (2/2), the jurisdiction section scores 3/3 and the national section 2/2; Q-E08 and Q-M09 remain parked for the web channel. Cards and notes live in a separate external store and do not enter the corpus index. The evaluation question set is still a draft and has not been reviewed by domain experts. Its code is public; the corpus, the processed store and the run reports stay local.

### Corpus at a glance

| Item | Value |
|---|---|
| Registered sources | 63 — 63 acquired, 0 candidates |
| Fishery yearbooks | 9 editions, data years 2017–2025, 838 files |
| China Statistical Yearbook | 2026 edition |
| Legal and technical documents | 53 — 1 law, 20 regulations, 12 notices, 17 standards, 2 data dictionaries, 1 operations reference |
| Local core CSV | 3,126 rows, not published |
| Documented gaps | port classes 2018–2019; vessel length 2024; 2025 sampled |
| Evaluation instrument | 11 anchor questions, 4 abstention tests; question set still a draft |

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
| [Corpus inventory](docs/corpus.md) | Registered sources, licences, sensitivity and coverage |
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

`make check` runs lint, format check, tests and the public-tree validation. `requirements.txt` carries the readers used for the register (PyYAML, openpyxl, xlrd) plus the optional fastembed ONNX encoder for the dense arm; CI installs `requirements-dev.txt` and runs the public checks without a model download.

The pipeline reads sources from `SCS_FKB_DATA_ROOT` and writes the processed store there; no data and no index enter the repository:

```sh
export SCS_FKB_DATA_ROOT=/path/to/local/data
make ingest   # parse the twenty-eight indexed documents and build the local chunks
PYTHONPATH=src python3 -m scs_fkb embed   # build the local dense index once
make eval     # four-arm Recall@5, MRR, abstention, citation and reference metrics
make define TERM=上岸量   # CWP definition passages for a Chinese term
PYTHONPATH=src python3 -m scs_fkb stats "2019年南海区海洋捕捞产量"   # local statistics rows
```

`make ingest` and `make eval` need the local data root; CI runs `make check` only, so the public tree stays data-free.

The default answer arm is **clause dump**: each retrieved clause is quoted sentence by sentence with its own `[DOC §section]` citation, the highest-overlap sentence is placed on top, and a deterministic numeric-comparison block renders Chinese numerals, Latin units and table-header units without inventing values. No model call is made for the answer. The arm keeps `SCS_FKB_DUMP_DEPTH=100`, `SCS_FKB_DUMP_MODE=block`, `SCS_FKB_DUMP_HITS=120` and `SCS_FKB_DUMP_CHARS=120000`; `SCS_FKB_ANSWER_MODE=extractive|llm|facet|quotes` switches arms. `SCS_FKB_DUMP_TOPIC` is a diagnostic and stays off.

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
| M1 | Minimal pipeline: parse, chunk, index, retrieve, answer with citations | done |
| M2 | Retrieval baseline: BM25 / dense / hybrid comparison | done |
| M3 | Evaluation report and service prototype | in progress |
| M4 | `/v1` query interface contract for downstream integration | deferred |

Milestones describe work stages, not releases. M1 and M2 are complete; the current phase is M3, with the evaluation question set still a draft pending expert review. The M4 contract is limited to `docs/interface.md` and `configs/interface.yaml` when it is added; it does not include data integration.

## Citation

If you use this project, please cite it using [CITATION.cff](CITATION.cff).

## License

- Code: [Apache License 2.0](LICENSE).
- Documentation: [Creative Commons Attribution 4.0 International](LICENSE-docs).
- Data: not distributed with this repository; see [docs/data-policy.md](docs/data-policy.md).

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md), [CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md), [SECURITY.md](.github/SECURITY.md) and [GOVERNANCE.md](GOVERNANCE.md).
