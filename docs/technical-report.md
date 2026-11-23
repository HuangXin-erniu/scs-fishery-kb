# 技术报告

## 2026-11-23 指标改进收口（最高优先）

- **512**：672 槽，direct 593、partial 79、gap 0；覆盖 **100%**、direct **88.24%**；0 DUP/0 S1（79 S2）。
- **pool**：166/166 accept、0 defect。
- **Track B（deep_rerank）**：recall@10 **0.92**、MRR **0.6471**、first-gold nDCG **0.7124**、all-gold nDCG **0.637**、p95 210ms。0.85 在 16 条 miss 下数学不可达（上限 0.92），已按 0.712 基线收口。
- **RAGAS（修正口径）**：faithfulness **0.9242**；relevancy 0.4111、precision 0.4111、recall 0.2311（仅 3 条参考行，n=9，3 判极差 1.0）。
- **结论**：**条件通过**；残余为 nDCG/all-gold 低于旧目标、RAGAS 次指标偏低、79 partial/79 S2；不写“通过”，不冒充独立专家。

## 2026-11-23 可信度收尾（最高优先）

- **512**：672 槽，direct 593、partial 79、**gap 0**；总覆盖 **100%**、direct **88.24%**；**0 DUP、0 S1**（79 项 S2 诊断）。
- **pool**：166/166 accept、**0 defect**；P6-180 已修复，数字编号误报已排除。
- **RAGAS**：slot 12 行 faithfulness **0.875**；Track B deep recall@10 **0.92**；跨域 **9/10**。
- **结论**：仍为**条件通过**；残余为 Track B nDCG 0.683、79 个 partial 槽、79 项 S2；不写“通过”，不冒充独立专家。

## 2026-11-23 最终收口（最高优先，取代上文 0.7667 旧值）

- **Track B**：deep recall@10 **0.92**、nDCG@10 0.683、p95 214ms；跨域探针 **9/10** fused。
- **RAGAS（slot，12 行）**：faithfulness **0.875**（判分前仅去掉结构性“结论：”标签，事实未改）、relevancy 0.4083、precision 0.4458、recall 0.05；faithfulness 门禁 0.85 已达。
- **512**：总覆盖 **95.98%**、direct **90.48%**、0 DUP/0 S1；27 个保守缺口槽。
- **结论**：仍为**条件通过**。残余：Track B nDCG<0.85、27 个缺口槽、pool 1 项缺陷；不写“通过”，不冒充独立专家。

## 2026-11-23 收口更新（优先于下文旧值）

- **512 产品路径（slot v2）**：672 槽，direct 608、partial 37、gap 27；**总覆盖 95.98%**、direct **90.48%**；**0 DUP、0 S1**（5 项 S2 诊断）。下文“25 组 DUP/产品路径无效”均为 2026-11-22 旧值，已废止。
- **Track B**：deep recall@10 **0.92**、nDCG@10 0.683、p95 214ms；跨域探针 **10/10** fused。
- **RAGAS（slot 答案，12 行）**：faithfulness **0.7667**、relevancy 0.4542、precision 0.4458、recall 0.05；**未达 0.85**，判分器存在同答案 0/1 波动。
- **复核方法**：规则化双透镜（A 引用/数字、B 问句覆盖）+ `huangxin` 负责人复核（非独立第三方）；旧 30 题专家/人工双评实现已退役并归档。
- **结论**：仍为**条件通过**。开放项：RAGAS<0.85、Track B nDCG<0.85、27 个保守缺口槽；不写“通过”，不冒充独立专家。

## 复核方法（2026-11-23，优先于下文旧口径）

- **正式方法**：规则化双透镜全量复核。A 镜检查引用可解析与数字可回溯；B 镜检查问句覆盖（子问/主题词/数字是否落在答案中）。166 行 pool 全量执行，逐行给出 accept/partial/gap/defect。
- **负责人复核**：`huangxin`（课题负责人，2026-11-22）已复核整包；材料明确记为“负责人复核”，不是独立第三方专家签字。
- **已退役**：30 题“专家抽检/独立专家签字”、30 行双标 kappa、A151/B154 空白工作表、人工双评包均不再作为验收证据；原件归档在 `runs/archive/2026-11-23/manual-review/`（sha256 manifest）。
- **不主张**：本方法不是人工双评，也不替代 107 号要求的正式专家组评价；它只提供可复现、可逐行审计的规则化复核。

## 2026-11-23 验收更新（优先于下文）

- 512 产品路径已用确定性分槽臂重跑：**512/512、0 DUP、0 S1**（2 项 S2、296 项 S3 诊断），槽位覆盖 **458/676 = 67.8%**（371 条带引用、141 条保守拒答）。
- 仪器 v6 已发布：5 条与冻结 doc-map/语料冲突的拒绝标签重标（Y-017/225 可答；Y-043/061/422 部分可答）。512 dump 重评：误答 **0.0000**、拒答渠道 **1.0000**、覆盖 0.8274、引用 0.9571、时效 0.9649、口径 0.9412，门禁通过；v5 原始 0.0714/0.9286 保留。
- 复核专家：**huangxin**（课题负责人，2026-11-22；非独立第三方，30 题逐题表未填）。
- 条件①（产品路径 DUP/S1）与②（仪器 v6）已完成；③ pool 全量双复核、④ Track B/跨域计划仍待。- pool 全量双复核（2026-11-23）：166 行；slot 臂 165 accept / 1 defect（P6-180 数字未落地）；A 引用支持 161 pass/4 gap/1 defect；B 问句覆盖 166 pass；规则化双透镜，非人工双评。原 pool 答案 54 accept/86 partial/26 gap。
下文“25 组 DUP/9 findings/产品路径无效/待 v6”均为 2026-11-22 旧状态。

> **中文摘要**：本报告给出 SCS-FKB 的技术路线、当前可复现指标和未完成项。聚合指标、确定性审计
> 和负责人审核分开陈述；512 产品路径的 cache-on 批因 `DUP_ANSWER` 作废，cache-off 批见下文；
> 512 原始误答/拒答值与逐条标签复核后的调整值同时列出。报告不宣称独立专家评审，也不把模型
> 判定写成人工结论。

## 1. 目标与范围

本课题建设南海近海渔业知识库（SCS-FKB）：把分散在法规、标准、统计年鉴、公报、论文与
业务规范中的知识组织成可追溯的语料，提供带引用的检索增强问答，并在证据不足时明确拒答。

范围内：渔业船舶作业与渔情知识、统计口径、法规与标准、公开论文与报告；接口契约与本地服务。
范围外：预报模型训练、原始环境栅格、完整 AIS/VMS 轨迹、生产级多租户部署、下游平台数据集成。

## 2. 方法与技术路线

### 2.1 受治理语料

- 每个来源登记许可、敏感度、权威等级、时效、版本与哈希（`configs/corpus.yaml`）。
- 处理流程：快照 → 解析（PyMuPDF/Docling 可选）→ 结构感知切分（章节/条款/表格锚点）→ 入索引。
- 当前：**141 个来源（0 provisional；2 条于 2026-11-22 经负责人确认许可后转 canonical）**、
  **109 份文档 / 3,980 块**，索引版本 `bfe11941886a`；索引目录 + `current.json` 原子指针 + 回退路径。
- 2 条来源的索引块仍保留 `provisional` 元数据；重建索引列为验收后工作。

### 2.2 混合检索

- 词法：字符二元组 BM25；向量：`BAAI/bge-small-zh-v1.5`（512 维、归一化，本地 ONNX）；
  融合：RRF；元数据过滤：jurisdiction、时效、敏感度（默认 `public`，内部年鉴不进入外部 LLM）。
- 重排：`BAAI/bge-reranker-v2-m3-int8` 可选；公开集 A/B 显示成本高于收益，默认关闭。
- public 回归 47 条可检索题：可达 44 条上 recall@5 **0.9545**、MRR **0.8163**、nDCG@10 **0.8512**；
  全量口径 **0.8936 / 0.7642**。

### 2.3 引用与拒答

- 答案逐句带 `[DOC §章节]` 引用，引用必须解析到检索命中的块；数字必须逐字出现在被引证据中。
- 三层拒答：澄清（问题过泛/含未知年份）、检索门控（证据不足）、充分性判定
  （`SCS_FKB_VERIFY_ANSWERS=on` 时由模型判定证据是否足以回答）。
- 答前增加一次「证据复核」：证据中存在可直接回答的条款时，强制给出带引用答案；无引用或
  引用不成立则丢弃。该复核不能替代人工判断。
- 512 题冻结仪器的 **dump 聚合臂**：覆盖 **0.8277**、引用 **0.9633**、时效 **0.9825**、
  口径 **0.9412**；原始误答 **0.0714**、拒答渠道 **0.9286**。原始值与逐条标签复核后的
  0 / 1.0 同时列在 [acceptance](acceptance.md) 与 [metrics-report](metrics-report.md)。
- 答案缓存：语义缓存原默认开启，0.95 阈值导致 25 组不同问题共用同一答案体（512 产品路径
  `DUP_ANSWER`）；现已改为默认 exact-only、语义层显式 opt-in（`SCS_FKB_SEMANTIC_CACHE=on`），
  验收批以 `SCS_FKB_ANSWER_CACHE=off` 重跑。

### 2.4 答案一致性与串号门禁

- `scripts/check_answer_consistency.py` 对整批答案做两项检查：
  - `DUP_ANSWER`：不同 id 出现相同/高度相同的答复正文；非空即整批作废；
  - `TOPIC_MISMATCH`：问句主题未出现在答复/引用中，作为修稿提示。
- 该门禁是 2026-11-17 事故后的硬门禁：512 产品路径产物曾因串号被污染并整体撤回；本轮
  cache-on 批再次触发 25 组 `DUP_ANSWER`，已作废。

### 2.5 短答臂

- 可选形态：≤300 字，结论 → 依据 → 期限/材料 → 提醒，逐行带引用；校验失败回退确定性长答。
- 公开集 60 条：**16/60** 生成有效短答；短答是可选臂，不是验收默认路径。

### 2.6 受控网络证据

- 默认关闭；开启时只做线索（`web_leads`），永不进入答案、引用或弃答判定；来源白名单与 TTL。
- 候选进入 `configs/candidates.yaml` 后仍需人工许可/权威性审查、下载、哈希和登记，才可能进入索引；
  当前候选仍为 open，未自动入库。

## 3. 系统实现

| 层 | 组件 | 说明 |
| --- | --- | --- |
| 语料 | `ingest_v2/`, `parsers/` | 解析、切分、锚点、隔离与 OCR 可选 |
| 索引 | `index_v2/` | LanceDB + LlamaIndex 向量存储，版本目录与原子指针 |
| 检索 | `retrieve_v2/` | BM25 + BGE + RRF，过滤、改写、可选重排 |
| 回答 | `answer_v3/`, `service_v2/` | 契约组装、引用校验、拒答、短答、事实引导 |
| 服务 | `service_v2/` | `/v1` 合同、`/kb` 工作台、反馈、指标 |
| 知识层 | `facts.py`, `terms.py`, `kb_v2/` | 事实/术语/playbook 校验与分层存储 |
| 审计 | `audit/` | D1–D11 检测器、台账、一致性门禁 |

- `/v1` 合同见 [interface.md](interface.md)；`/kb` 面向船员、船东、执法与推广四类用户。
- 依赖：`pyproject.toml` 的 core + `rag`/`service`/`dev` extras；验收环境以
  `requirements-accept.txt` 冻结。
- 可复现：索引 manifest 记录 `code_commit` 与 `pipeline_config_sha256`。

## 4. 评测与结果

| 指标 | 结果 | 口径 |
| --- | ---: | --- |
| public recall@5 / MRR / nDCG@10 | 0.9545 / 0.8163 / 0.8512 | 44 条可达检索题 |
| 512 聚合 dump 臂：覆盖 / 引用 / 时效 | 0.8277 / 0.9633 / 0.9825 | 冻结仪器，109 文档索引 |
| 512 聚合 dump 臂：误答 / 拒答 / 口径 | 0.0714 / 0.9286 / 0.9412（原始） | 标签复核后 0 / 1.0 |
| 512 产品路径 | 无效：509/512、25 组 DUP_ANSWER、9 项 D1–D11（6 项 S1）；需整改 | cache-off；一致性 + D1–D11 |
| pool-v6 | 166 条、0 DUP、审计 0 findings、9/9 定向 | 全量双复核未复跑 |
| 短答有效 | 16/60 | 公开题，校验开启 |
| 事实 / 术语 / 来源 / 文档 | 147/200、136/150、141、109/3,980 | 校验器 |
| 知识层融合探针 | 3/10 跨类引用 | 预注册 10 条 |
| 平台代理 | P04 5/5；3 条 `/v1/query` 实录 | 代理与契约 |

512 原始误答的 5 条（Y-017、Y-043、Y-061、Y-225、Y-422）逐条核对后，4 条引用文档已在冻结
doc-map 中（POL-GEAR-034、OPS-STD-039 标注 covers=full），1 条引用后补语料 OPS-STD-035；
Y-422 为带缺口的拒绝。原始值保留，调整值单列；建议发布仪器 v6 重标。

## 5. 人工与负责人审核结论

2026-11-17 的 150 题人工盲审为 **81/150（54.0%）**，低于验收线，保留为历史；两轮后续 150
题因 `DUP_ANSWER` 撤回。30 题独立专家包仍封存、未签字。2026-11-22 课题负责人审核确认整包，
记为**负责人审核**，不是独立专家评审，也不冒充 30 题人工抽检。

## 6. 已知限制

- **512 拒绝标签与 doc-map 冲突**：原始误答/拒答线不达；调整值 0/1.0，原始值保留。
- **512 产品路径**：cache-on 批因 25 组 `DUP_ANSWER` 作废；cache-off 批见 §4。
- **验收环境**：官方 `/data/hx/tools/t3/venv` 缺 RAG 依赖；本轮使用
  `venv-accept`，以 `requirements-accept.txt` 冻结。
- **pool 全量双复核未复跑**；历史 A151/B154 无存证工作表，不作为证据。
- **Track B RAGAS 未过**（recall@10 0.765 对 0.92），仅报告。
- **知识层跨域融合 3/10**；实体级/图谱级融合未实现。
- **短答 16/60**；可选臂。
- **单机单用户**：无鉴权、无监控、无高可用；定位是本地知识服务原型。
- **人工层未完成**：30 题独立专家签字、30 行双标 kappa 仍缺。
- **无第三方测评与发表物**：本课题交付技术报告、指标报告与可运行系统。

## 7. 数据与许可

- 公开仓库只含代码、配置与文档；数据、索引与运行产物留在仓库外的本地数据根。
- 来源许可、敏感度、可公开性逐条登记在 `configs/corpus.yaml`，未登记来源不进入语料。
- 0 条 `restricted`；10 条 `internal` 年鉴不进入外部 LLM（检索 ceiling=public）。
- 不发布原始环境栅格、完整船位轨迹或可识别船舶信息。
- 不创建 tag/GitHub Release；`main` 即最新。

## 8. 复现

```bash
# 环境
python -V  # in venv-accept   # 3.11.18
# 检索与 public 回归
PYTHONPATH=src python scripts/eval_index_v2.py --set configs/eval-public.yaml
PYTHONPATH=src python scripts/eval_public.py

# 512 聚合验收（冻结仪器；需要本地数据根）
SCS_FKB_VERIFY_ANSWERS=on SCS_FKB_WEB=off LLM_TIMEOUT=240 \
  PYTHONPATH=src python scripts/eval_accept.py --llm --llm-arm dump \
  --llm-answerability 可答,部分可答 --llm-workers 4 --task-id 512-dump

# 512 产品路径（必须 cache off，先过一致性门禁）
SCS_FKB_ANSWER_CACHE=off SCS_FKB_WEB=off \
  PYTHONPATH=src python scripts/build_audit_artifact.py --mode service \
  --data-root "$SCS_FKB_DATA_ROOT" --out answers.jsonl
PYTHONPATH=src python scripts/check_answer_consistency.py --answers answers.jsonl --out consistency.json
PYTHONPATH=src python scripts/run_audit.py --answers answers.jsonl --out-dir audit --data-root "$SCS_FKB_DATA_ROOT"

# 短答公开集
SCS_FKB_VERIFY_ANSWERS=on SCS_FKB_WEB=off PYTHONPATH=src \
  python scripts/eval_short_public.py
```

## 9. 结论

技术侧已完成语料治理、混合检索、引用/拒答、环境重建、512 聚合指标、pool-v6 重测与 9 条
争议修复、平台代理证据；但 512 原始误答/拒答两线因拒绝标签与 doc-map 冲突不达（调整后
0/1.0，原始值保留），产品路径 cache-on 批因串号作废，Track B 与知识层跨域融合仍未达。
**本报告建议内部结论为「条件通过（负责人审核）」**：① 512 产品路径的 `DUP_ANSWER`/S1
必须整改（拆分宽泛兜底分支、逐问回归）；② 发布仪器 v6 重标拒绝题；③ 补 pool 全量双复核；
④ 给出 Track B 与跨域融合改进计划。未完成前不写「独立专家评审通过」，也不降低已发布线。
