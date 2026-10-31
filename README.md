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
> 当前完成 M1 法律子集：3 份法规/通告已本地索引，支持 BM25 检索与抽取式引用回答；dense 与 LLM 尚未实现。
> 仓库不发布任何数据或运行产物；完整中文说明见 [README.zh-CN.md](README.zh-CN.md)。

## Status

**M1 legal subset implemented.** Three public policy documents are registered and indexed locally: the Fisheries Law (2025 revision), the seasonal closure notice (2023) and the fishing permit regulation (2022). The pipeline provides HTML body extraction, article/section chunking, BM25 retrieval, extractive answers with resolved citations, and explicit abstention. Dense retrieval, LLM generation, the HTTP service and the `/v1` contract are not implemented yet.

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
├── src/scs_fkb/                 M1 ingestion, BM25, citation and CLI modules
├── scripts/                     public-tree validation
└── tests/                       pipeline, configuration and public-tree tests
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

`make check` runs lint, format check, tests and the public-tree validation. The M1 core uses only the Python standard library and PyYAML; the other packages in `requirements.txt` are optional adapters for later PDF, dense-retrieval, LLM and service work.

After registering acquired sources under `$SCS_FKB_DATA_ROOT`, run the local pipeline:

```sh
export PYTHONPATH=src
python -m scs_fkb ingest
python -m scs_fkb retrieve "南海 伏季休渔 时间"
python -m scs_fkb ask "南海区伏季休渔的起止时间是什么？"
```

The pipeline reads the corpus register, verifies source hashes and writes processed chunks and a manifest outside the repository. It does not download sources or call a model.

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
| M1 | Minimal pipeline: parse, chunk, BM25 retrieve, extractive citations | current (legal subset) |
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

See [CONTRIBUTING.md](.github/CONTRIBUTING.md), [CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md), [SECURITY.md](.github/SECURITY.md) and [GOVERNANCE.md](GOVERNANCE.md).
