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

**本阶段语料与数据准备（WP1）已完成；检索管线仅以本地原型运行。** 已登记 84 个来源：81 个已获取、3 个候选（全部暂缓）。已获取部分为 9 版渔业统计年鉴（数据年 2017–2025，838 个文件——837 个 Excel 表与 1 份扫描 PDF）、6 份全国渔业经济统计公报（数据年 2020–2025）、中国统计年鉴 2026，以及 57 份法规与技术文件——1 部法律、20 份法规、15 份通告、18 套标准（含 17 项 SC/T 标准，295 页，图像版参考 PDF，以及 CWP 统计定义）、1 份作业表单说明、1 份渔港规划、3 份参考字典，4 份远端数据栈文档（MUR SST 产品页、OLCI 海洋手册、GFW Events API 文档、CMEMS 产品手册、中文海洋一号（HY-1C/D）产品能力说明），以及 5 份统计制度与监测文档（2010 年渔业统计工作规定、2024 年渔业统计调查制度、2017 年度渔情监测通报、2019 年远洋渔船船位监测办法、2025 年电子证照标准）。每个来源都记录许可、敏感级、版本与 SHA-256；年鉴为 internal、仅本地使用。覆盖矩阵与 3,126 行本地核心 CSV（2017–2024 加 2025 抽样）均在公开库之外。已记录三处缺口：2018–2019 年无渔港表、2024 年无海洋渔船船长表、2025 年为抽样。充分性复核已接受：24 道草拟问题中 10 道可答、6 道部分可答、8 道作为拒答题。M1 现以抽取式原型在本机运行：38 份已入库的公开来源解析为 896 个块，带条款、分节与页码锚点；有金标锚点的 11 道题中，BM25 与稠密混合检索的锚点级 Recall@5 为 10/11（MRR 0.45）；三个参考集合配合项目自建的中英术语桥回答定义与产品类问题（CWP 2/2、product 2/2）；本地统计通道用年鉴版次与表名引用回答统计问题（2/2），并明确说明年鉴未刊出的两个维度；所有引用均可解析，四臂评测结果见下文。代码公开，语料、处理结果与运行报告均留在本地。

### 语料一览

| 项目 | 数值 |
|---|---|
| 已登记来源 | 84——81 个已获取、3 个候选（全部暂缓） |
| 渔业统计年鉴 | 9 版，数据年 2017–2025，838 个文件 |
| 全国渔业统计公报 | 6 份，数据年 2020–2025 |
| 中国统计年鉴 | 2026 版 |
| 法规与技术文件 | 26 份——1 部法律、10 份法规、4 份通告、6 套标准、1 份作业表单说明、1 份渔港规划、3 份参考字典 |
| 已获取 SC/T 标准 | 17 项（295 页，图像版参考 PDF） |
| 本地核心 CSV | 3,126 行，不公开 |
| 已记录缺口 | 2018–2019 年渔港分类；2024 年船长；2025 年为抽样 |
| 充分性复核 | 10 道可答、6 道部分可答、8 道拒答题 |

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

`make check` 运行 lint、格式检查、测试与公开树校验。`requirements.txt` 只列登记册所需的读取工具（PyYAML、openpyxl、xlrd）；管线本身只用标准库。

管线从 `SCS_FKB_DATA_ROOT` 读取来源、把处理结果写回该目录，数据与索引都不进入仓库：

```sh
export SCS_FKB_DATA_ROOT=/path/to/local/data
make ingest   # 解析已入库的 33 份文档并生成本地分块
PYTHONPATH=src python3 -m scs_fkb embed   # 首次运行生成本地稠密索引
make eval     # 四臂 Recall@5、MRR、拒答、引用与参考通道指标
make define TERM=上岸量   # 查询中文术语对应的 CWP 定义段落
PYTHONPATH=src python3 -m scs_fkb stats "2019年南海区海洋捕捞产量"   # 本地统计行
```

`make ingest` 与 `make eval` 需要本地数据根；CI 只运行 `make check`，公开树因此不含数据。

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
| M1 | 最小链路：解析、切分、索引、检索、带引用回答 | 下一步：待所有者决定 |
| M2 | 检索基线：BM25 / 向量 / 混合对照 | 计划中 |
| M3 | 评测报告与服务原型 | 计划中 |
| M4 | 面向下游集成的 `/v1` 查询接口契约 | 计划中 |

里程碑表示工作阶段，不是 Release。语料充分性复核已于 2026-11-01 接受，因此 M1 的启动取决于所有者决定，而非语料条件。M1 现以抽取式原型在本机运行：38 份已入库的公开来源解析为 896 个块，带条款、分节与页码锚点；有金标锚点的 11 道题中，BM25 与稠密混合检索的锚点级 Recall@5 为 10/11（MRR 0.45）；三个参考集合配合项目自建的中英术语桥回答定义与产品类问题（CWP 2/2、product 2/2）；本地统计通道用年鉴版次与表名引用回答统计问题（2/2），并明确说明年鉴未刊出的两个维度；所有引用均可解析，四臂评测结果见下文。代码公开，语料、处理结果与运行报告均留在本地。M4 契约在加入时只包含 `docs/interface.md` 与 `configs/interface.yaml`，不做数据集成。

## 引用

使用本项目时请引用 [CITATION.cff](CITATION.cff)。

## 许可

- 代码：[Apache License 2.0](LICENSE)。
- 文档：[Creative Commons Attribution 4.0 International](LICENSE-docs)。
- 数据：不随本仓库发布；详见 [docs/data-policy.md](docs/data-policy.md)。

## 参与

见 [CONTRIBUTING.md](.github/CONTRIBUTING.md)、[CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md)、[SECURITY.md](.github/SECURITY.md) 与 [治理](GOVERNANCE.md)。
