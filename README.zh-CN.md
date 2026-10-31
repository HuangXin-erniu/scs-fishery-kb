# 南海近海渔船作业与渔情知识库（SCS-FKB）
**South China Sea Nearshore Fishery Knowledge Base (SCS-FKB)**

[English](README.md) | [简体中文](README.zh-CN.md)

[![CI](https://github.com/HuangXin-erniu/scs-fishery-kb/actions/workflows/ci.yml/badge.svg)](https://github.com/HuangXin-erniu/scs-fishery-kb/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey.svg)](LICENSE-docs)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

面向**南海近海渔船作业**与**渔情**的检索增强知识库。

本项目把文档、数据字典、产品说明、渔情通报、政策法规、标准与研究报告中可公开的知识层内容，整理成可检索、可引用、可评测的领域知识库，并提供带出处证据的检索增强问答。

## 状态

**M1 法律子集已实现。** 三份公开政策文件已登记并在本地索引：渔业法（2025 修订）、伏季休渔通告（2023）与捕捞许可规定（2022）。当前支持 HTML 正文抽取、按条/节切分、BM25 检索、带可解析引用的抽取式回答，以及显式拒答。向量检索、LLM 生成、HTTP 服务与 `/v1` 契约尚未实现。

本项目不设版本号：不创建 tag、不发布 GitHub Release，也不使用语义化版本。`main` 即最新状态；引用时请使用 commit SHA。变更记录见 [项目日志](docs/project-log.md)。

**本仓库不发布任何数据或运行产物。** 详见 [docs/data-policy.md](docs/data-policy.md)。

## 范围

**纳入**

- 知识层语料治理：来源、许可、敏感级、元数据、版本与哈希。
- 文档解析、结构感知切分、表格与指标抽取。
- 混合检索（BM25 + 向量）与元数据过滤，可选重排。
- 带引用、可拒答、可评测的检索增强问答。
- 面向下游平台集成的 `/v1` 查询接口契约（只定义契约，不做数据集成）。

**不纳入**

- 渔情预报模型训练或推理服务。
- 原始环境栅格、预报产品、全量 AIS/VMS 轨迹的发布。
- 生产级多租户平台、鉴权或监控。
- 与下游平台的数据集成；该工作另行处理。

## 框架与方案

| 文档 | 用途 |
|---|---|
| [项目范围](PROJECT.zh-CN.md) · [English](PROJECT.md) | 目标、范围、非目标与数据政策 |
| [架构](docs/architecture.md) | 分层、组件、数据流、数据契约与运行方式 |
| [项目计划](docs/plan.md) | 工作包、里程碑、角色、质量门与风险 |
| [评测](docs/evaluation.md) | 问题集、指标、协议、目标与报告 |
| [语料盘点](docs/corpus.md) | 已获取与候选来源、许可、敏感级与优先级 |
| [项目日志](docs/project-log.md) | 按日期记录的项目变更 |
| [治理](GOVERNANCE.md) | 角色、决策、版本政策与边界 |
| [术语表](docs/glossary.md) | 渔业与检索概念的中英术语 |
| [架构决策](docs/adr/README.md) | 重要决策的记录 |
| [文档规范](docs/style-guide.md) | 语言、链接、引用与提交约定 |

## 仓库结构

```text
scs-fishery-kb/
├── README.md / README.zh-CN.md
├── PROJECT.md / PROJECT.zh-CN.md
├── GOVERNANCE.md               角色、决策与边界
├── LICENSE / LICENSE-docs      代码 Apache-2.0；文档 CC BY 4.0
├── CITATION.cff
├── .github/                    社区文件、CI、Issue 与 PR 模板
├── configs/                    语料登记与 schema
├── docs/                       架构、计划、评测、政策、术语表、ADR
├── src/scs_fkb/                M1 摄入、BM25、引用与 CLI 模块
├── scripts/                    公开树校验
└── tests/                      管线、配置与公开树测试
```

数据与运行产物只在本机使用，不进入公开树。

## 快速开始

```sh
git clone https://github.com/HuangXin-erniu/scs-fishery-kb.git
cd scs-fishery-kb

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

make check
```

`make check` 运行 lint、格式检查、测试与公开树校验。M1 核心只使用 Python 标准库与 PyYAML；`requirements.txt` 中的其余包是后续 PDF、向量检索、LLM 与服务工作的可选适配器。

在 `$SCS_FKB_DATA_ROOT` 下登记已获取来源后，可运行本地管线：

```sh
export PYTHONPATH=src
python -m scs_fkb ingest
python -m scs_fkb retrieve "南海 伏季休渔 时间"
python -m scs_fkb ask "南海区伏季休渔的起止时间是什么？"
```

管线读取语料登记、校验来源哈希，并把处理后的 chunks 与 manifest 写到仓库外。它不下载来源，也不调用模型。

## 数据与产物

- 数据与运行产物放在仓库外，从不提交。
- `SCS_FKB_DATA_ROOT` 与 `SCS_FKB_RUN_ROOT` 指向本地数据根与运行产物根；见 `.env.example`。
- 每个来源的许可与敏感级记录在 `configs/corpus.yaml`。
- `license: unknown` 或 `sensitivity: unknown` 的来源一律 hold，不得入库。
- `restricted` 来源只能本地处理，不得发送到外部模型 API。
- 公开仓库不包含数据、索引或运行产物。

详见 [docs/data-policy.md](docs/data-policy.md)。

## 路线图

| 里程碑 | 交付物 | 状态 |
|---|---|---|
| M0 | 框架：范围、架构、计划、评测、语料登记、工具链 | 完成 |
| M1 | 最小链路：解析、切分、BM25 检索、抽取式引用回答 | 当前（法律子集） |
| M2 | 检索基线：BM25 / 向量 / 混合对照 | 计划中 |
| M3 | 评测报告与服务原型 | 计划中 |
| M4 | 面向下游集成的 `/v1` 查询接口契约 | 计划中 |

里程碑表示工作阶段，不是 Release。M4 契约在加入时只包含 `docs/interface.md` 与 `configs/interface.yaml`，不做数据集成。

## 引用

使用本项目时请引用 [CITATION.cff](CITATION.cff)。

## 许可

- 代码：[Apache License 2.0](LICENSE)。
- 文档：[Creative Commons Attribution 4.0 International](LICENSE-docs)。
- 数据：不随本仓库发布；详见 [docs/data-policy.md](docs/data-policy.md)。

## 参与

见 [CONTRIBUTING.md](.github/CONTRIBUTING.md)、[CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md)、[SECURITY.md](.github/SECURITY.md) 与 [治理](GOVERNANCE.md)。
