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
> 当前管线与 512 题私有验收已完成；可选网络证据层默认关闭，只作带标注的线索。
> 仓库不发布任何数据或运行产物；完整中文说明见 [README.zh-CN.md](README.zh-CN.md)。

## Status

**Pipeline and acceptance complete for this phase.** One hundred sources are registered: ninety-eight acquired and two held. Sixty-seven documents are indexed (2,797 chunks). The service answers in clause-dump mode: verbatim sentences with `[DOC §section]` citations, the highest-overlap sentence on top and a deterministic numeric-comparison block. Under acceptance protocol v2 the private 512-question run passes all six lines: misanswer 0.0000, refusal-with-channel 1.0000, as-of 0.9474, point coverage 0.8092, citation 0.9565 and basis 0.9412. Protocol v2 judges citation location at document level, gives partial credit to point terms and measures basis over answered numeric rows; the rules and the v1 comparison are in [docs/evaluation.md](docs/evaluation.md). The code is public; the corpus, the processed store and the run reports stay local. An optional short-answer arm returns at most 300 characters with a citation per claim (`ask --short` or `"short": true`); the default remains the deterministic evidence path. A worker-facing knowledge station at `/kb` groups task cards, sourced FAQ, plain terms, numeric quick reference and what-changed by persona. Index builds are immutable per version, switched by an atomic pointer and kept for rollback. An optional web-evidence layer is available but off by default (`SCS_FKB_WEB=off`): it may return up to two labelled leads from an official-host allowlist, never counts as a corpus citation, never enters the answer text and never ingests automatically.

Phase updates are announced in [GitHub Discussions](https://github.com/HuangXin-erniu/scs-fishery-kb/discussions/12).

### Corpus at a glance

| Item | Value |
|---|---|
| Registered sources | 100 — 98 acquired, 2 held |
| Fishery yearbooks | 9 editions, data years 2017–2025, 838 files |
| China Statistical Yearbook | 2026 edition |
| Legal and technical documents | 53 — 1 law, 20 regulations, 12 notices, 17 standards, 2 data dictionaries, 1 operations reference |
| Local core CSV | 3,126 rows, not published |
| Documented gaps | port classes 2018–2019; vessel length 2024; 2025 sampled |
| Indexed documents | 67 documents, 2,797 chunks |
| Evaluation instrument | Private 512-question acceptance set; six-line protocol |

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
PYTHONPATH=src python3 scripts/build_v2.py        # parse registered sources into the local store
PYTHONPATH=src python3 scripts/build_index_v2.py  # build the local BM25 + dense index
PYTHONPATH=src python3 -m scs_fkb ask "2026年南海区伏季休渔从什么时候开始？"
PYTHONPATH=src python3 -m scs_fkb ask --full "2026年南海区伏季休渔从什么时候开始？"
PYTHONPATH=src python3 -m scs_fkb serve   # UI at /, demo at /demo, OpenAPI at /docs, metrics at /metrics
```

`ask` prints a short contract summary and the main citations; `--full` prints the
full evidence text. The build commands need the local data root; CI runs
`make check` only, so the public tree stays data-free.

The default answer arm is **clause dump**: each retrieved clause is quoted sentence by sentence with its own `[DOC §section]` citation, the highest-overlap sentence is placed on top, and a deterministic numeric-comparison block renders Chinese numerals, Latin units and table-header units without inventing values. No model call is made for the answer. The arm keeps `SCS_FKB_DUMP_DEPTH=300`, `SCS_FKB_DUMP_MODE=block`, `SCS_FKB_DUMP_HITS=300` and `SCS_FKB_DUMP_CHARS=100000`; `SCS_FKB_ANSWER_MODE=extractive|llm|facet|quotes` switches arms. `SCS_FKB_DUMP_TOPIC` is a diagnostic and stays off.

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
