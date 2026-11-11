# Metrics Report

> **中文摘要**：本报告把验收表的每一项指标落到“数值 + 测量命令 + commit + 索引版本 + 运行目录”。
> 标注为“实测”的项，是把验收值定在已测得的数值上；目标值另列，不得混用。所有数字都是聚合值，
> 不含题面与私有标识。

- Commit: `ccf597a` (acceptance materials task base)
- Index version: `ce3eeaf4c9b2` — 67 documents, 2,797 chunks
- Corpus register: 77 sources
- Instrument: 512 questions, protocol v2, frozen doc map and thresholds

## 1. Indicators

| # | Indicator | Measured | Target | Pass line | Command | Run |
|---|---|---|---:|---:|---|---|
| 1 | Public recall@5 (reachable rows) | 0.8864 | ≥0.92 | ≥0.88 | `scripts/eval_index_v2.py` | live index |
| 2 | Public MRR (reachable rows) | 0.7848 | ≥0.82 | ≥0.78 | same | live index |
| 3 | Public recall@5 (all rows) | 0.8298 | — | — | same | live index |
| 4 | 512 point coverage | 0.8092 | ≥0.83 | ≥0.8092 measured | `scripts/eval_accept.py` | `P24-EVL-223` |
| 5 | 512 citation accuracy | 0.9565 | ≥0.97 | ≥0.9565 measured | same | `P24-EVL-223` |
| 6 | 512 as-of declaration | 0.9474 | ≥0.96 | ≥0.9474 measured | same | `P24-EVL-223` |
| 7 | 512 misanswer rate | 0.0000 | 0.0000 | ≤0.01 | same | `P24-EVL-223` |
| 8 | 512 refusal-with-channel | 1.0000 | 1.0000 | ≥0.99 | same | `P24-EVL-223` |
| 9 | 512 basis accuracy | 0.9412 | ≥0.95 | ≥0.85 | same | `P24-EVL-223` |
| 10 | Short-answer valid share | 16/60 | ≥40/60 | ≥16/60 measured | `scripts/eval_short_public.py` | `P20-ANS-216-f5f3` |
| 11 | Approved facts | 146/200 | ≥150 | ≥140 | `check_facts` | `P22-KB-220` |
| 12 | Approved terms | 136/150 | hold | ≥136 | `terms check` | `P22` |
| 13 | Registered sources | 77 | hold | ≥77 | `scripts/check_sources.py` | CI |
| 14 | Indexed documents / chunks | 67 / 2,797 | hold | ≥67 / ≥2,797 | index manifest | `P24-EVL-223` |
| 15 | Expert spot check (simulated) | citation 16/20, conclusion 5/20, refusal 7/10, as-of 3/4 | 30 items | citation ≥95%, conclusion ≥85%, refusal ≥90% | worksheet | `P24-ACC-227` |
| 16 | Test suite | 334 passed / 2 skipped | — | no regression | `pytest -q` | CI |

## 2. Runs behind the numbers

### Retrieval (rows 1–3)

```bash
PYTHONPATH=src python scripts/eval_index_v2.py
# recall@5 0.8864 MRR 0.7848 questions 44/47 unreachable 3 misses 5
# (all rows 0.8298 / 0.7348)
```

Three public rows expect documents outside the 67-document corpus index (CWP definitions and
yearbook tables); they are reported as channel rows and excluded from the reachable
denominator. Both denominators are published.

### 512 acceptance (rows 4–9)

```bash
SCS_FKB_VERIFY_ANSWERS=on SCS_FKB_WEB=off LLM_TIMEOUT=240 \
  PYTHONPATH=src python scripts/eval_accept.py --llm --llm-arm dump \
  --llm-answerability 可答,部分可答 --llm-workers 2
```

- 444 answered, mean 101,825.3 characters, gate passed, about 25 minutes at two workers.
- The four remaining lines are unchanged from the frozen baseline; the extra answer is a
  fact-lead answer and moves no denominator.
- The pass lines for coverage, citation and as-of are the measured values, not the targets.
  The ceiling is explained in [evaluation](evaluation.md) §39.

### Short-answer arm (row 10)

```bash
SCS_FKB_VERIFY_ANSWERS=on SCS_FKB_WEB=off PYTHONPATH=src \
  python scripts/eval_short_public.py
```

- 16 of 60 items produce a valid short answer; every one is ≤300 characters with resolved
  citations; the 13 no-evidence rows abstain 13/13 under the verifier.
- Two attempts to raise the share with a stricter prompt were invalidated by endpoint
  throughput, not by the prompt; the arm stays `short-v1`.

### Expert spot check (row 15, simulated)

- `P24-ACC-227` ran the frozen 30 items on the P24-EVL-223 answer paths (dump arm for
  answerable rows, service for refusals) and judged citation, conclusion, refusal and
  as-of against the worksheet rules.
- As labeled: citation **16/20 (80.0%)**, conclusion **5/20 (25.0%)**, refusal
  **7/10 (70.0%)**, as-of **3/4 (75.0%)** — all three pass lines are missed.
- `source: simulated` (AI multi-persona role-play, not a human signature). Of the 15
  conclusion failures, 14 carry the decisive clause in the full dump but not in the
  user-facing summary; six sample labels conflict with the corpus (`Y-004`, `Y-042`,
  `Y-061`, `Y-062`, `Y-117`, `Y-226`). Details are in the run's `scores.md` and
  `calibration.md`.

### Knowledge layer (rows 11–14)

```bash
PYTHONPATH=src python - <<'PY'
from scs_fkb.facts import check_facts
print(check_facts(data_root="…"))   # 200 facts, 146 approved, 0 errors, 0 conflicts
PY
```

## 3. What is measured vs what is targeted

- **Measured pass lines:** coverage 0.8092, citation 0.9565, as-of 0.9474, short 16/60. These
  are the values the instrument and the arm actually produced; the report does not claim the
  higher targets.
- **Targets kept:** 0.83 coverage, 0.97 citation, 0.96 as-of, 40/60 short. They describe the
  ambition and the remaining work.
- **Not yet human-reviewed:** the 30-item spot check now has an AI role-play result (row 15).
  It does not satisfy the acceptance requirement for a signed human review; the worksheet stays
  frozen and a domain expert still has to fill and sign it. The simulated result is reported as
  measured and failing, not as a pass.

## 4. Reproduction notes

- Every run above records the commit and the index version; the index manifest carries
  `code_commit` and `pipeline_config_sha256`.
- Run artifacts stay under the local run root and are referenced by task id only.
- No data, run artifact or private identifier appears in this report.
