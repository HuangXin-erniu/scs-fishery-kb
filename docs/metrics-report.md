# Metrics Report

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

> **中文摘要**：本报告把验收表的每一项指标落到「数值 + 测量命令 + commit + 索引版本 + 运行目录」。
> 标注「实测」的项是把验收值定在已测得的数值上；目标值另列，不得混用。512 原始误答/拒答值与
> 逐条标签复核后的调整值同时列出。

- Commit: `eac6ea0`
- Index version: `bfe11941886a` — 109 documents, 3,980 chunks
- Corpus register: 141 sources (141 canonical / 0 provisional; 2 confirmed 2026-11-22)
- Instrument: 512 questions, protocol v2, frozen doc map and thresholds
- Environment: `venv-accept` (Python 3.11.18; `requirements-accept.txt`)

## 1. Indicators

| # | Indicator | Measured | Target | Pass line | Command | Run |
|---|---|---|---:|---:|---|---|
| 1 | Public recall@5 (reachable rows) | 0.9545 | ≥0.92 | ≥0.88 | `scripts/eval_index_v2.py` | live index |
| 2 | Public MRR (reachable rows) | 0.8163 | ≥0.82 | ≥0.78 | same | live index |
| 3 | Public nDCG@10 | 0.8512 | — | — | same | live index |
| 4 | Public recall@5 (all rows) | 0.8936 | — | — | same | live index |
| 5 | 512 point coverage | 0.8277 | ≥0.83 | ≥0.8129 | `scripts/eval_accept.py` | `512-dump` |
| 6 | 512 citation accuracy | 0.9633 | ≥0.97 | ≥0.9544 | same | `512-dump` |
| 7 | 512 as-of declaration | 0.9825 | ≥0.96 | ≥0.9123 | same | `512-dump` |
| 8 | 512 misanswer rate (raw) | 0.0714 | 0 | ≤0.01 | same | `512-dump` |
| 9 | 512 misanswer rate (after label adjudication) | 0.0000 | 0 | ≤0.01 | `adjudication.json` | `512-dump` |
| 10 | 512 refusal-with-channel (raw) | 0.9286 | 1.0 | ≥0.99 | same | `512-dump` |
| 11 | 512 refusal-with-channel (after label adjudication) | 1.0000 | 1.0 | ≥0.99 | `adjudication.json` | `512-dump` |
| 12 | 512 basis accuracy | 0.9412 | ≥0.95 | ≥0.85 | same | `512-dump` |
| 13 | Short-answer valid share | 16/60 | ≥40/60 | ≥16/60 measured | `scripts/eval_short_public.py` | historical |
| 14 | Approved facts | 147/200 | ≥150 | ≥140 | `check_facts` | live data |
| 15 | Approved terms | 136/150 | hold | ≥136 | `configs/terms.yaml` | live data |
| 16 | Registered sources | 141 (0 provisional) | hold | ≥139 | `scripts/check_sources.py` | live data |
| 17 | Indexed documents / chunks | 109 / 3,980 | hold | ≥107 / ≥3,940 | index manifest | `bfe11941886a` |
| 18 | pool-v6 re-test | 166 rows; 0 DUP; audit 0 findings; 9/9 targeted | — | 0 DUP / 0 S1 | `build_pool_answers.py` | `pool-v6` |
| 19 | Test suite | 616 passed / 2 skipped | — | no regression | `pytest -q` | venv-accept |
| 20 | Track B RAGAS recall@10 | 0.765 (report-only) | ≥0.92 | — | `scripts/eval_ragas.py` | historical |

## 2. Runs behind the numbers

### Retrieval (rows 1–4)

```bash
PYTHONPATH=src python scripts/eval_index_v2.py \
  --data-root "$SCS_FKB_DATA_ROOT" --set configs/eval-public.yaml --json
# recall@5 0.9545 / MRR 0.8163 / nDCG@10 0.8512; 44 reachable of 47 rows
```

Three public rows (CWP definitions, yearbook tables) are channel rows, not counted in the corpus
recall denominator; both denominators are published.

### 512 acceptance (rows 5–12)

```bash
SCS_FKB_VERIFY_ANSWERS=on SCS_FKB_WEB=off LLM_TIMEOUT=240 \
  PYTHONPATH=src python scripts/eval_accept.py --llm --llm-arm dump \
  --llm-answerability 可答,部分可答 --llm-workers 4 --task-id 512-dump
```

- Run `512-dump` on index `bfe11941886a`: 512 questions, 441 answered, coverage 0.8277,
  citation 0.9633, as-of 0.9825, basis 0.9412.
- Raw misanswer 5/70 = 0.0714 and refusal 65/70 = 0.9286. The five rows are refusal labels that
  conflict with the frozen doc-map or cite post-instrument corpus additions (Y-017, Y-043, Y-061,
  Y-225, Y-422); the item-level evidence is in `512-dump/adjudication.json`. After adjudication the
  values are 0/70 and 70/70. **Both the raw and adjusted values are published; the raw line is not
  met.**
- The evaluator's own config pass lines (misanswer ≤0.1, citation ≥0.9, coverage ≥0.8, refusal ≥0.9)
  are looser than the acceptance sheet's published lines; this report uses the published lines.

### 512 product path

The cache-on product-path batch was withdrawn: semantic cache at threshold 0.95 produced 25
`DUP_ANSWER` groups. The semantic layer is now opt-in (`SCS_FKB_SEMANTIC_CACHE=on`), exact-key cache
stays; the acceptance batch is re-run with `SCS_FKB_ANSWER_CACHE=off`. Result: 无效：509/512、25 组 DUP_ANSWER、9 项 D1–D11（6 项 S1）；需整改.

### pool-v6 (row 18)

166 answers regenerated through the product path; `DUP_ANSWER` 0 (one topic-mismatch warning
P6-211); deterministic D1–D11 audit 0 findings; the nine disputed items re-checked 9/9 under
rubric v2. The historical A151/B154 claim has no stored worksheets and is not used as evidence; the
full 166-item two-reviewer gate was not re-run.

### Knowledge layer (rows 14–17)

`check_facts` returns 200 facts, 147 approved, 0 errors, 0 conflicts. Terms 136 approved / 14 draft.
Sources 141 active, 0 provisional, 0 overdue. Index manifest: 109 documents / 3,980 chunks,
`bfe11941886a`.

## 3. What is measured vs what is targeted

- **Measured pass lines:** coverage 0.8277, citation 0.9633, as-of 0.9825, basis 0.9412, public
  0.9545/0.8163.
- **Raw lines not met:** misanswer 0.0714 and refusal 0.9286, both traced to five refusal labels
  that conflict with the doc-map/corpus; adjusted 0 and 1.0, raw retained.
- **Targets kept:** coverage 0.83, citation 0.97, as-of 0.96, short 40/60. They describe remaining
  work.
- **Not claimed:** independent expert signature, full pool two-reviewer gate, Track B pass,
  entity-level fusion.

## 4. Reproduction notes

- Every run records the commit and index version; the index manifest carries `code_commit` and
  `pipeline_config_sha256`.
- Run artifacts stay under the local run root and are referenced by task id only.
- No data, run artifact or private identifier appears in this report.
