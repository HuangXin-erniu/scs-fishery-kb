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

**本阶段管线与验收已完成。** 已登记 100 个来源：98 个已获取、2 个保留。索引 67 份文档（2,797 个块）。服务默认按条文摘录回答：逐句引用原文并标注 `[DOC §章节]`，问题重合度最高的句子置顶，另附确定性的数值对照块。在验收协议 v2 下，512 题私有验收六条线全部通过：误答 0.0000、拒答渠道 1.0000、时效 0.9474、要点覆盖 0.8129、引用 0.9588、口径 0.9412。v2 的引用按文档级定位、点位词给部分命中、口径只计可答数值行；规则与 v1 对照见 [docs/evaluation.md](docs/evaluation.md)。代码公开，语料、处理结果与运行报告留在本地。

### 语料一览

| 项目 | 数值 |
|---|---|
| 已登记来源 | 100——98 个已获取、2 个保留 |
| 渔业统计年鉴 | 9 版，数据年 2017–2025，838 个文件 |
| 中国统计年鉴 | 2026 版 |
| 法规与技术文件 | 53 份——1 部法律、20 份法规、12 份通告、17 项标准、2 部数据字典、1 份作业参考 |
| 本地核心 CSV | 3,126 行，不公开 |
| 已记录缺口 | 2018–2019 年渔港分类；2024 年船长；2025 年为抽样 |
| 索引规模 | 67 份文档、2,797 个块 |
| 评测工具 | 私有 512 题验收集；六条协议线 |

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
| [语料盘点](docs/corpus.md) | 已登记来源、许可、敏感级与覆盖 |
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
├── scripts/                    公开树校验
└── tests/                      配置与公开树测试
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

`make check` 运行 lint、格式检查、测试与公开树校验。`requirements.txt` 列出登记册所需的读取工具（PyYAML、openpyxl、xlrd）以及可选的 fastembed ONNX 编码器（用于稠密检索）；CI 安装 `requirements-dev.txt`，不下载模型。

管线从 `SCS_FKB_DATA_ROOT` 读取来源、把处理结果写回该目录，数据与索引都不进入仓库：

```sh
export SCS_FKB_DATA_ROOT=/path/to/local/data
PYTHONPATH=src python3 scripts/build_v2.py        # 解析已登记来源，生成本地处理结果
PYTHONPATH=src python3 scripts/build_index_v2.py  # 生成本地 BM25 + 稠密索引
PYTHONPATH=src python3 -m scs_fkb ask "2026年南海区伏季休渔从什么时候开始？"
PYTHONPATH=src python3 -m scs_fkb ask --full "2026年南海区伏季休渔从什么时候开始？"
PYTHONPATH=src python3 -m scs_fkb serve
```

`ask` 默认输出合同摘要与主要引用；`--full` 输出完整依据。构建命令需要本地数据根；
CI 只运行 `make check`，公开树因此不含数据。

默认回答臂为**条文摘录**：检索到的每条条款逐句引用，每句带 `[DOC §章节]` 引用，问题重合度最高的句子置顶；另附确定性的"数值对照"块，把中文数字、拉丁单位和表头单位渲染成可核对写法，不引入原文没有的数值。回答不调用模型。默认 `SCS_FKB_DUMP_DEPTH=300`、`SCS_FKB_DUMP_MODE=block`、`SCS_FKB_DUMP_HITS=300`、`SCS_FKB_DUMP_CHARS=300000`；`SCS_FKB_ANSWER_MODE=extractive|llm|facet|quotes` 可切换其他回答臂。`SCS_FKB_DUMP_TOPIC` 仅为诊断开关，保持关闭。

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
| M1 | 最小链路：解析、切分、索引、检索、带引用回答 | 完成 |
| M2 | 检索基线：BM25 / 向量 / 混合对照 | 完成 |
| M3 | 评测报告与服务原型 | 进行中 |
| M4 | 面向下游集成的 `/v1` 查询接口契约 | 暂缓 |

里程碑表示工作阶段，不是 Release。M1 与 M2 已完成；当前处于 M3，评测题目集仍为草案，待业务专家复核。M4 契约在加入时只包含 `docs/interface.md` 与 `configs/interface.yaml`，不做数据集成。

## 引用

使用本项目时请引用 [CITATION.cff](CITATION.cff)。

## 许可

- 代码：[Apache License 2.0](LICENSE)。
- 文档：[Creative Commons Attribution 4.0 International](LICENSE-docs)。
- 数据：不随本仓库发布；详见 [docs/data-policy.md](docs/data-policy.md)。

## 参与

见 [CONTRIBUTING.md](.github/CONTRIBUTING.md)、[CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md)、[SECURITY.md](.github/SECURITY.md) 与 [治理](GOVERNANCE.md)。
