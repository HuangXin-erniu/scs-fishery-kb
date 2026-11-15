# ADR 0010: Dual-track evaluation with industry-standard metrics

> 中文摘要：512 冻结仪器保留为内部回归/课题验收（Track A），新增 RAGAS + 检索 + 引用/拒答 + 人工抽检的 Track B 作为产品主门禁；两套数字分开报告，不混算。

- Status: Proposed
- Date: 2026-11-12

## Context

The current acceptance programme scores the 512-question instrument with six
project-defined lines (point coverage, citation accuracy, as-of declaration,
misanswer, refusal-with-channel, basis accuracy). The instrument is frozen and
its coverage is structurally capped near 0.813: 79 of 132 uncovered points use
terms that appear nowhere in the indexed corpus. The project also carries a
"RAGAS-compatible" judge, but the `ragas` library is not installed, the judge is
report-only and there is no nDCG or context-precision gate. An external reader
cannot compare the result with common RAG evaluation practice.

## Decision

- **Track A (regression / acceptance material)**: keep the frozen 512
  instrument, its labels, the dump arm and the six lines unchanged. Track A is
  the internal regression and the materials-review artifact; it is not the
  product gate and it is not retuned.
- **Track B (product gate)**: build a separate dataset and metric suite:
  - retrieval: 300 rows; Recall@1/5/10, MRR, nDCG@10, hit rate;
  - generation: 200 rows; RAGAS faithfulness, answer relevancy, context
    precision, context recall, answer correctness;
  - citation: 200 rows; resolution, precision, unsupported-claim rate;
  - abstention: 100 rows; false-answer, false-refusal, refusal accuracy,
    channel coverage;
  - human: a 30-item stratified spot check with the rubric v2 (locate the core
    slot, then judge); `source: human` is the only signature, `simulated` stays
    separate.
- The dataset is seeded, stratified and frozen with a manifest hash. The frozen
  core comes from the private instrument; the pending rows are filled from the
  practical-source batches. Track B is not a merge gate until `gate_ready` is
  true.
- RAGAS 0.4.x runs in an **isolated virtual environment** because it pins an
  older langchain/openai stack; the main runtime is not downgraded. The repo
  ships `requirements-ragas.txt` and `scripts/ragas_runner.py`; the main
  environment only orchestrates it as a subprocess.
- Targets are ambitions; pass lines are frozen after the Phase 0 baseline and
  published next to the measured values. A model-judged score is supporting
  evidence, never a substitute for a human signature.
- CI runs only deterministic metrics (fixed retrieval/citation/abstention
  fixtures); the full RAGAS run is local or scheduled, with a judge cache.

## Consequences

- Two numbers are published for two different questions; the reports state
  which artifact each number scores.
- The 512 instrument remains comparable across code changes; product quality is
  measured on the reader-facing answer.
- Judge variance and cost are bounded by a fixed prompt, temperature 0, a
  cache, repeated runs and a confidence interval; judge failure is reported as
  an error, not as a score.
- The project no longer claims "industry standard" from self-defined metrics
  alone; it points to the RAGAS definitions and the retrieval/citation/
  abstention formulas.

## Alternatives considered

- **Replace the 512 instrument**: loses comparability and the materials-review
  evidence; rejected.
- **Only RAGAS**: misses retrieval quality, citation correctness and refusal
  behaviour; rejected.
- **Public benchmark cross-evaluation (RGB, CRAG, MultiHop-RAG)**: valuable but
  needs data licences and a separate harness; deferred as an optional later
  decision.

## References

- [Track B schema](../../configs/eval-industry.yaml)
- [Evaluation](../evaluation.md)
- [RAGAS](https://docs.ragas.io/)
- [RAG standard](../rag-standard.md) section 8
