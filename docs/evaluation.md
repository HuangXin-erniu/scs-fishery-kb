# Evaluation

> **中文摘要**：本文件定义检索、引用、回答与拒答的评测问题集、指标、协议与目标。
> 评测以人工复核为准；报告必须记录 commit、索引版本、模型与问题集版本，保证可复现。
> 目标值是最低门槛，不是对外承诺；未达标指标要通过误差分析解释，不得改指标掩盖。

- Status: protocol defined; the question set is a draft and has not been reviewed by domain experts.
- Baseline (2026-11-01, M2 comparison over twenty-nine public sources): four arms on the same instrument — BM25 8/11, BM25 plus lexicon 9/11, dense-only 8/11 and hybrid 10/11, each with abstention 3/4, two false refusals and 100% citation resolution; hybrid MRR 0.45 and P95 17 ms.

| Arm | Recall@5 | MRR | Abstention | False refusals | P95 |
|---|---|---|---|---|---|
| BM25 | 8/11 | 0.37 | 3/4 | 2 | — |
| BM25 + lexicon | 9/11 | 0.40 | 3/4 | 2 | — |
| Dense (bge-small-zh) | 8/11 | 0.37 | 3/4 | 2 | 16 ms |
| **Hybrid (adopted)** | **10/11** | **0.45** | **3/4** | **2** | **17 ms** |
- Statistics channel (2026-11-01): the two statistical questions are scored separately. Q-E06 runs 南海区海洋捕捞产量历年趋势 and expects the sea-area production series; Q-M05 runs 2019年南海区拖网渔船数量 and expects vessel counts. Both return rows with edition and table citations (2/2). The channel also states the two gaps: production has no operation-type dimension and vessel counts have no sea-area dimension.
- Reference collections (2026-11-02): four questions are scored outside the main index. Q-E05 and Q-M04 use the CWP definition collection; Q-E08 and Q-M09 use the product collection (MUR, OLCI and CMEMS documentation) and both return a passage from the expected documents (4/4). The collections are measured separately from the main ranked metrics, which do not change.
- Abstention denominator: Q-E08 and Q-M09 moved from the abstention list to the product collection, so four out-of-scope tests remain (Q-E07, Q-E11, Q-M07, Q-M08) and three abstain; Q-E07 is still the known answered test. The percentage is therefore not comparable with earlier 5/6 figures.
- Answer assembly (2026-11-02): when a question asks for a period and not for an implementation date, the extractive answer searches every retrieved hit for a sentence carrying a date range and, if found, cites it first. Q-E01 now leads with the South China Sea clause from [POL-CLOS-015 §三、休渔时间] instead of the implementation date in §四; the retrieval, reference, statistics and abstention metrics are unchanged.
- Related: [evaluation questions](questions.md), [project plan](plan.md), [data policy](data-policy.md).

## 1. Purpose

Evaluation answers three questions:

1. Does retrieval return the right evidence?
2. Do answers cite that evidence correctly and avoid fabrication?
3. Does the system abstain when the corpus cannot support an answer?

Human review is authoritative for answer correctness. Automated metrics are supporting evidence, not a substitute for expert review.

## 2. Question set

The draft set contains 24 questions: 12 for vessel operators and captains, 12 for fisheries administration. It covers policy, procedure, definition, statistic, fact and standard questions.

Before use:

- Domain experts review each question for realism and specificity.
- Unanswerable questions are kept as abstention tests, not deleted.
- Gold answers and evidence pages are added only when a reliable source exists.
- The set is expanded to 30–50 reviewed questions for the first baseline, with a target of 100+.
- Sensitive questions are excluded from the public repository; they remain in the local evaluation set.

The public draft is [questions.md](questions.md).

## 3. Metrics

### Retrieval

- Recall@k: whether the gold document/page appears in the top k results.
- MRR: mean reciprocal rank of the first relevant result.
- Hit@k: whether any relevant result appears in the top k.

### Citation

- Citation precision: the share of citations that resolve to a retrieved chunk.
- Citation coverage: the share of factual claims with at least one citation.
- Invalid-citation rate: citations that do not resolve or do not support the claim.

### Answer

- Correctness: agreement with the gold answer, judged by a human reviewer.
- Faithfulness: whether the answer is supported by the cited evidence.
- Completeness: whether the answer covers the required parts of the question.

### Abstention

- Out-of-scope refusal accuracy: the share of unanswerable questions that are refused.
- False-refusal rate: the share of answerable questions that are refused.

### Performance

- Retrieval latency, end-to-end latency, index build time and memory peak.

The instrument scores anchors, not answers: a question counts as retrieved when a top-5 chunk matches one of its gold anchors in `configs/eval.yaml` (document plus section prefix, or document plus page). Answer correctness, faithfulness and completeness still need reviewed gold answers. The three misses (Q-E10, Q-M10, Q-M12) are all ranking gaps caused by vocabulary mismatch between the question and the article: the 2013 mesh notice repeats the question's words while the standard tables do not, and the access and exception articles use different phrasing. That mismatch is the case for dense retrieval in M2.

## 4. Protocol

1. **Split the set:** development, test and held-out subsets. The held-out subset is not used for tuning.
2. **Establish baselines:** BM25-only, dense-only and hybrid retrieval.
3. **Run the pipeline:** record the question, retrieved chunks, answer, citations, abstention and latency.
4. **Review:** a domain expert marks correctness and faithfulness; disagreements are recorded.
5. **Analyse errors:** classify retrieval misses, citation errors, answer errors and unnecessary refusals.
6. **Report:** publish aggregate metrics, per-type results and representative errors with evidence.

A question is scored only if its gold answer and evidence are reviewed. Unreviewed questions are reported separately and do not count toward acceptance.

## 5. Initial targets

These targets are provisional and will be calibrated after the first reviewed corpus.

| Dimension | Target |
|---|---|
| Recall@5 | ≥ 0.85 |
| MRR | ≥ 0.70 |
| Citation precision | ≥ 0.90 |
| Citation coverage | ≥ 0.90 |
| Answer correctness | ≥ 0.80 |
| Faithfulness | ≥ 0.85 |
| Out-of-scope refusal accuracy | ≥ 0.90 |
| Retrieval P95 latency | < 2 s |
| End-to-end P95 latency | < 5 s |

A missed target is investigated with error analysis; it is not hidden by changing the metric.

## 6. Reproducibility

Each run records:

- commit identifier and index version,
- embedding model and generation model identifiers,
- retrieval configuration (top-k, fusion, filters, reranking),
- commands and configuration files,
- evidence hashes for the retrieved chunks.

A report is reproducible when another maintainer can rerun the same commands against the same corpus and index version.

## 7. Data and ethics

- The evaluation set contains no restricted or personal data in the public repository.
- Public examples use synthetic or clearly public content.
- Restricted questions and answers stay local.
- Human reviewers do not copy restricted source text into public reports.
- Any data used in evaluation follows [data-policy.md](data-policy.md).

## 8. Reporting template

A run report should include:

1. Scope and corpus version.
2. Question-set version and split.
3. Configuration and model/index versions.
4. Aggregate metrics and per-type breakdown.
5. Representative successes and failures with citations.
6. Limitations and next actions.

## 9. References

- [Evaluation questions](questions.md)
- [Project plan](plan.md)
- [Corpus register](../configs/corpus.yaml)
- [Data schema](../configs/schema.yaml)
- [Data policy](data-policy.md)
