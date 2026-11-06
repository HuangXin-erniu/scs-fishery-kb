# Reranker Calibration — 2026-11-06

> **中文摘要**：在 31 道已复核锚点题上比较 no-rerank、pure rerank、short rerank 和保留词法前若干名的变体。没有任何变体同时满足“31/31 锚点 + 不低于 no-rerank 的 MRR + 交互级 P95”。因此 **reranker 默认继续关闭**，`--rerank` 仅保留给离线实验；本次不改检索代码或默认配置。

## 1. Scope

- Index: v2 LanceDB table `23e933753e22`, 785 child chunks, BGE-small-zh embeddings.
- Reranker: `BAAI/bge-reranker-v2-m3-int8` via fastembed.
- Questions: the 31 reviewed anchor questions in `configs/eval.yaml` / `docs/questions.md`.
- Machine: local Mac M2, 8 GB RAM, no GPU.
- Arms:
  - `none`: hybrid RRF without reranker.
  - `pure`: rerank top-10 fused hits, 300 chars per hit.
  - `preserve1` / `preserve2`: pure rerank, then pin the fused top-1 or top-2 hit back into the final five.
  - `short6`: rerank top-6 fused hits, 500 chars per hit.
  - `short6_preserve1`: short6 plus the fused top-1 pinned back.

## 2. Results

| Arm | Anchors | MRR | Rerank P95 |
|---|---:|---:|---:|
| `none` | **31/31** | **0.9301** | 0 ms (no rerank) |
| `pure` | 29/31 | 0.8495 | 2714 ms |
| `preserve1` | 30/31 | 0.8817 | 2714 ms |
| `preserve2` | 30/31 | 0.8978 | 2714 ms |
| `short6` | **31/31** | 0.9140 | 2976 ms |
| `short6_preserve1` | **31/31** | 0.9140 | 2976 ms |

Full 48-question run for the two committed arms:

| Arm | Anchors | MRR | P95 | Abstention |
|---|---:|---:|---:|---:|
| no rerank | 31/31 | 0.7511 | 18.2 ms | 8/11 |
| `--rerank` | 29/31 | 0.8360 | 2574.5 ms | 8/11 |

The subset MRR (0.9301) is higher than the full-set MRR (0.7511) because the
subset excludes non-anchor questions; the two numbers are not comparable.

## 3. Decision

**Keep the reranker off by default.** No arm meets all three conditions:

1. anchor recall 31/31;
2. MRR at least the no-rerank arm (0.9301 on this subset);
3. interactive P95 <= 500 ms.

`short6` preserves 31/31 anchors but lowers MRR to 0.9140 and adds ~3 s per
query. `pure` improves some ranks but loses two anchors. Pinning the fused top
hit back does not recover the pure-rerank losses. The optional `--rerank` flag
remains available for offline experiments; it is not the product default.

## 4. Reproduction

No-rerank and pure-rerank arms:

```bash
SCS_FKB_DATA_ROOT=... SCS_FKB_RUN_ROOT=... PYTHONPATH=src \
  python scripts/eval_index_v2.py --report /tmp/v2_norerank.md

SCS_FKB_DATA_ROOT=... SCS_FKB_RUN_ROOT=... PYTHONPATH=src \
  python scripts/eval_index_v2.py --rerank --report /tmp/v2_rerank.md
```

The `short6` and preservation arms were measured with a temporary harness that
calls `Reranker(max_candidates=6, max_chars=500)` and pins the fused top hit; the
harness is deliberately not part of the product path. The committed
`scripts/eval_index_v2.py --rerank` reproduces the pure arm.

## 5. Limits

- One machine, one model, one index version; latency will differ on other hosts.
- The 31-question subset is anchor-level, not a full answer-quality judgment.
- The reranker is an optional second-stage ranker; this decision does not remove
  the code, the flag or the tests.
