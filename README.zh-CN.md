# 南海近海渔船作业与渔情知识库（SCS-FKB）

[![CI](https://github.com/HuangXin-erniu/scs-fishery-kb/actions/workflows/ci.yml/badge.svg)](https://github.com/HuangXin-erniu/scs-fishery-kb/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-lightgrey.svg)](LICENSE-docs)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

面向**南海近海渔船作业**与**渔情**的检索增强知识库。

本项目把文档、数据字典、产品说明、渔情通报、政策法规、标准与研究报告中可公开的知识层内容，整理成可检索、可引用、可评测的领域知识库，并提供带出处证据的检索增强问答。

## 状态

`v0.1.0-alpha`：公开基线，包含研究范围、语料登记、评测问法、文档、配置、工具链与 CI。检索流水线与服务代码在下一里程碑加入。

**本仓库不发布任何数据或运行产物。** 详见 [docs/data-policy.md](docs/data-policy.md)。

## 范围

**纳入**

- 知识层语料治理：来源、许可、敏感级、元数据、版本与哈希。
- 文档解析、结构感知切分、表格与指标抽取。
- 混合检索（BM25 + 向量）与元数据过滤，可选重排。
- 带引用、可拒答、可评测的检索增强问答。
- 面向下游平台集成的版本化查询接口契约（只定义契约，不做数据集成）。

**不纳入**

- 渔情预报模型训练或推理服务。
- 原始环境栅格、预报产品、全量 AIS/VMS 轨迹的发布。
- 生产级多租户平台、鉴权或监控。
- 与下游平台的数据集成；该工作另行处理。

## 仓库结构

```text
scs-fishery-kb/
├── README.md / README.zh-CN.md
├── PROJECT.md                  研究范围与路线图
├── LICENSE / LICENSE-docs      代码 Apache-2.0；文档 CC BY 4.0
├── CITATION.cff
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── .github/                    CI、Issue 与 PR 模板
├── configs/                    语料登记与 schema
├── data/                       不发布载荷；仅政策说明
├── docs/                       语料、问法、方法、数据政策、路线图
├── scripts/                    公开树校验
└── tests/                      配置与公开树测试
```

`data/` 与 `runs/` 只在本机使用。数据载荷、索引、运行日志与 state 数据库都不进入 Git。

## 快速开始

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

`requirements.txt` 中的运行依赖会在检索代码落地时安装。当前基线只有文档与配置。

## 数据与产物

- `data/` 放本地源文件与索引；除 `data/README.md` 外全部 gitignore。
- `runs/` 放本地运行产物；整个目录 gitignore。
- 每个来源的许可与敏感级记录在 `configs/corpus.yaml`。
- `license: unknown` 或 `sensitivity: unknown` 的来源一律 hold，不得入库。
- `restricted` 来源只能本地处理，不得发送到外部模型 API。
- 公开仓库不包含数据、索引或运行产物。

详见 [docs/data-policy.md](docs/data-policy.md)。

## 路线图

| 里程碑 | 交付物 | 状态 |
|---|---|---|
| M0 | 公开基线：范围、语料登记、评测问法、工具链 | `v0.1.0-alpha` |
| M1 | 最小链路：解析、切分、索引、检索、带引用回答 | 计划中 |
| M2 | 检索基线：BM25 / 向量 / 混合对照 | 计划中 |
| M3 | 评测报告与服务原型 | 计划中 |
| M4 | 面向下游集成的版本化查询接口契约 | 计划中 |

M4 契约在加入时只包含 `docs/interface.md` 与 `configs/interface.yaml`，不做数据集成。

## 引用

使用本项目时请引用 [CITATION.cff](CITATION.cff)。

## 许可

- 代码：[Apache License 2.0](LICENSE)。
- 文档：[Creative Commons Attribution 4.0 International](LICENSE-docs)。
- 数据：不随本仓库发布；详见 [docs/data-policy.md](docs/data-policy.md)。

## 参与

见 [CONTRIBUTING.md](CONTRIBUTING.md)、[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 与 [SECURITY.md](SECURITY.md)。

English README: [README.md](README.md).
