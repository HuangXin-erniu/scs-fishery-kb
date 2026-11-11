# Acceptance Sheet

> **中文摘要**：本页是本课题的验收指标表与验收程序。每项指标写“现状 / 目标值 / 验收值”，
> 评审以验收值为准，目标值体现提升幅度。验收形式为材料评审加 30 题专家抽检，不设现场演示；
> 模型判定的分数在报告中一律标注为“模型判定”，不得当作人工复核。阈值沿用项目已发布的
> 协议 v2 与 RAGAS 兼容定义，不引用无法核验的“行业标准数字”。

## 1. Review form

- **Materials-only review.** The panel reads the technical report, the metrics report,
  the demonstration script, the evidence map, the data/licence note and the known-limits
  list. No live demonstration is scheduled; the script and recorded output stand in.
- **30-item expert spot check.** A domain expert samples 30 questions from the reviewed
  instrument across the four personas and judges citation correctness, conclusion
  correctness, refusal appropriateness and as-of declaration. The worksheet is signed and
  attached to the metrics report. Two simulated runs (AI role-play, `P24-ACC-227` and the
  held-out `P25-ACC-231`) are recorded separately; neither is a signature and neither
  replaces this step.
- **Two layers of evidence.** Deterministic and model-judged metrics come from the
  reproducible runs below; the spot check is the only human-judged layer. A model score is
  never reported as human review.

## 2. Indicators

| Indicator | Current | Target | Pass | Measurement | Evidence |
|---|---:|---:|---:|---|---|
| Public-set recall@5 | 0.8864 (all rows 0.8298) | ≥0.92 | **≥0.88** | `scripts/eval_index_v2.py` (44 reachable of 47 rows) | [evaluation](evaluation.md) §37 |
| Public-set MRR | 0.7848 (all rows 0.7348) | ≥0.82 | **≥0.78** | same run | §37 |
| 512 point coverage | 0.8092 (measured 2026-11-11) | ≥0.83 | **≥0.8092 (measured)** | `scripts/eval_accept.py` (protocol v2, 727 judgeable points) | §29, §34 |
| 512 citation accuracy | 0.9565 (measured 2026-11-11) | ≥0.97 | **≥0.9565 (measured)** | same run (437 cited rows) | §29 |
| 512 as-of declaration | 0.9474 (measured 2026-11-11) | ≥0.96 | **≥0.9474 (measured)** | same run (57 as-of rows) | §29 |
| 512 misanswer rate | 0.0000 | 0.0000 | **≤0.01** | same run (70 refusal rows) | §29 |
| 512 refusal-with-channel | 1.0000 | 1.0000 | **≥0.99** | same run | §29 |
| Short-answer valid share | 16/60 (measured 2026-11-11) | ≥40/60 | **≥16/60 (measured)** | `scripts/eval_short_public.py` with `SCS_FKB_VERIFY_ANSWERS=on` | §35, §36 |
| Approved facts | 146/200 | ≥150 | **≥140** | `scs-fkb facts check` (0 errors, 0 conflicts) | [knowledge](knowledge.md) |
| Approved terms | 136/150 | hold | **≥136** | `scs-fkb terms check` | knowledge |
| Registered sources | 77 | hold | **≥77** | `scripts/check_sources.py` | [corpus](corpus.md) |
| Indexed documents and chunks | 67 / 2,797 | hold | **≥67 / ≥2,797** | index manifest | `v2/index/versions/<id>/manifest.json` |
| Expert spot check | simulated 2026-11-11 (AI role-play, not human): holdout citation 50.0%, conclusion 45.0%, refusal 20.0% — **below all three lines** | 30 items | **citation ≥95%, conclusion ≥85%, refusal ≥90%** | review worksheet | `P25-ACC-231`, [metrics report](metrics-report.md) §2 |
| Reproducibility | available | one command | **one command + commit + index hash** | `docs/plan.md` §8 | run artifacts |

Three public rows (CWP definitions, yearbook tables) expect documents that are not in the
67-document corpus index; they are served by the reference and statistics channels and are
reported as channel rows, not counted in the corpus recall denominator. Both numbers are
published.

Target and pass values are separate on purpose: the target is the improvement the work aims
for, the pass value is the bar the review applies. Coverage is structurally capped by the
instrument's term anchoring (about 0.858 with the current corpus); the pass value sits below
that cap and the report states the cap.

## 2b. Material package

| Item | File | Status |
|---|---|---|
| Metrics report | [metrics-report.md](metrics-report.md) | complete |
| Technical report | [technical-report.md](technical-report.md) | skeleton with content; narrative sections marked |
| Demo script | [demo-script.md](demo-script.md) | complete, five scenarios |
| 30-item expert spot check | local worksheet under the run root | holdout sample frozen; simulated reviews complete (`P24-ACC-227` regression, `P25-ACC-231` holdout, both below the lines); human signature pending |

## 3. Evidence map

| Claim | Evidence |
|---|---|
| Corpus governance | `configs/corpus.yaml`, `scripts/check_sources.py`, [corpus.md](corpus.md) |
| Index build and versions | `v2/index/versions/<id>/manifest.json`, `v2/index/current.json` |
| Retrieval and coverage | [evaluation.md](evaluation.md) §29, §33, §34 |
| Short-answer arm | [evaluation.md](evaluation.md) §35, `scripts/eval_short_public.py` |
| Facts, terms, playbooks | [knowledge.md](knowledge.md), `configs/facts/`, `configs/terms.yaml` |
| Interface contract | [interface.md](interface.md), `configs/interface.yaml` |
| Public regression | `configs/eval-public.yaml`, `scripts/eval_public.py` |
| Boundaries and licences | [data-policy.md](data-policy.md), [GOVERNANCE.md](../GOVERNANCE.md) |

Run artifacts stay under the local run root and are referenced by task id, never committed.

## 4. Procedure

1. Submit the six material items listed in section 1.
2. The panel samples 30 questions; the expert fills the worksheet.
3. Score the spot check and compare every indicator with the pass column.
4. Record the outcome: pass, or conditional pass with each deviation written down and the
   measured value attached.

## 5. Known limits (not claimed)

- Coverage headroom is bounded by the instrument's term anchoring; new sources do not move it.
- The short-answer arm is optional and returns a valid short answer on part of the public set;
  the dump arm remains the default.
- Deployment is local and single-user; no authentication, monitoring or high availability.
- The external fact/term store never decides corpus abstention.
- No third-party benchmark and no published paper are claimed; the deliverables are the
  technical report, the metrics report and the running system.

## 6. Reproduction

```bash
# retrieval and public regression
PYTHONPATH=src python scripts/eval_index_v2.py --set configs/eval-public.yaml
PYTHONPATH=src python scripts/eval_public.py

# 512 acceptance (scoped LLM arm; see evaluation.md section 34)
SCS_FKB_DATA_ROOT=... SCS_FKB_RUN_ROOT=... SCS_FKB_VERIFY_ANSWERS=on SCS_FKB_WEB=off \
  PYTHONPATH=src python scripts/eval_accept.py --llm --llm-arm dump \
  --llm-answerability 可答,部分可答 --llm-workers 6

# short-answer arm on the public set
SCS_FKB_DATA_ROOT=... SCS_FKB_RUN_ROOT=... SCS_FKB_VERIFY_ANSWERS=on SCS_FKB_WEB=off \
  PYTHONPATH=src python scripts/eval_short_public.py

# validators
PYTHONPATH=src python -m scs_fkb facts check --data-root "$SCS_FKB_DATA_ROOT"
PYTHONPATH=src python -m scs_fkb terms check --data-root "$SCS_FKB_DATA_ROOT"
```
