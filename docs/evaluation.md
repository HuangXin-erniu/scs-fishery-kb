# Evaluation

> **中文摘要**：本文件定义检索、引用、回答与拒答的评测问题集、指标、协议与目标。
> 评测以人工复核为准；报告必须记录 commit、索引版本、模型与问题集版本，保证可复现。
> 目标值是最低门槛，不是对外承诺；未达标指标要通过误差分析解释，不得改指标掩盖。

- Status: protocol defined; the current question set was reviewed by the project owner in three batches (2026-11-04).
- Reviewed instrument (2026-11-04, 33 questions: 19 anchors, 8 abstention, 2 reference, 2 statistics, 2 deferred): hybrid **19/19** with MRR 0.68, abstention 7/8, one false refusal, answer rate 18/19, citation resolution 1.00, citation coverage 0.99, extractive faithfulness 1.00 and P95 20 ms; BM25 17/19 (MRR 0.64), BM25 plus lexicon 19/19 (0.69) and dense 15/19 (0.55). Reference 2/2, statistics 2/2, jurisdiction 3/3 and national 2/2. Q-E07 remains the one answered abstention test under the deterministic gate.
- LLM-assisted run (2026-11-04, `deepseek-v4.1-flash`, low reasoning effort, prompt `rag-v3`): hybrid **19/19** anchors, **8/8** abstention, **0 false refusals**, answer rate 19/19, citation resolution 1.00; model judge correctness **0.76**, completeness **0.66**, faithfulness **0.94**. Q-E07 now abstains because the evidence only lists other fishing grounds; Q-E12 answers from `POL-LAW-009` §第七十八条. These scores are model-assisted, not human review. Prompt-only completeness attempts (v4/v5) and top-document evidence expansion were measured and rejected: completeness fell to 0.61, 0.56 and 0.37, so the v3 baseline is retained. The remaining gap is evidence coverage, not prompt wording.
- Deterministic gold-point coverage (2026-11-04, 38 points across 19 anchors, eval-only `checks`): extractive **10/38 (0.26)**, LLM **15/38 (0.39)**. The missing points are concentrated in secondary items: Q-E02 four special-permit types, Q-E12 penalty ranges, Q-M01 article 44, Q-M12 article 26/78, Q-M17 inspection types. This is a diagnostic baseline, not a target; the checks never enter the product path.
- Held-out split (2026-11-04, P09-EVAL-130, 48 questions: 33 dev + 15 test): the test split has 12 anchors and 3 abstention across captain, owner, enforcement and extension. Extractive: dev 19/19, abstention 7/8, MRR 0.6816, coverage 10/38; test 12/12, abstention 1/3, MRR 0.8542, coverage 2/22. LLM: dev 19/19, 8/8, correctness/completeness/faithfulness 0.7605/0.6605/0.9421, coverage 15/38; test 12/12, 3/3, 0.7125/0.7083/0.8958, coverage 10/22. Hybrid MRR is 0.6816; the 0.6886 figure belongs to the BM25-plus-lexicon arm. Test is report-only and is not used for tuning.
- Clause-index experiment (2026-11-04): split long sections at item markers and kept parent chunks. Hybrid top-5 anchor recall fell from 19/19 to 16/19 and abstention from 7/8 to 6/8 because clause chunks changed BM25 ranking and external notes outranked corpus items. Index restored to `20910f0964df`; clause indexing is deferred until retrieval scoring/depth is changed with it.
- Baseline (2026-11-03, adopted; 28 public documents, 785 chunks, index `20910f0964df`, dense `58ded7342e4c66fe`): BM25 8/11, BM25 plus lexicon 10/11, dense-only 8/11 and hybrid **11/11** with MRR 0.56, abstention 3/4, two false refusals and 100% citation resolution; hybrid P95 19 ms; reference 2/2, statistics 2/2, jurisdiction 3/3 and national 2/2. Cards and notes are not in this index: they live in a separate external store (259 documents, 315 chunks, index `0c6d3901106c`) and are consulted only after a non-abstained corpus answer.
- Claim-matrix experiment (2026-11-03, 287 documents with cards and notes, index `0137968fd40c`): chunks now carry source class, trust tier and review date, and hits are filtered by claim nature before answering (definition/rule/quantity/status/warning/identification/history). BM25 and lexicon abstention stayed at 3/4, but hybrid remained 9/11 with abstention 2/4; the filter cannot separate the out-of-scope question because the enlarged dense candidate pool already changes corpus ranking. Not adopted.
- Layered-gate experiment (2026-11-03, 287 documents with cards and notes, index `0137968fd40c`): a corpus-only gate was added (a chunk kind plus a corpus-evidence check, pass-through from `answer.require_corpus_evidence`) and measured. It restored BM25 abstention to 3/4 but hybrid still fell to 2/4 and recall to 9/11, so the flag did not make the enlarged index safe. The gate code stays (it is exercised by tests) but the enlarged index is not adopted; the corpus-only row below remains the baseline.
- Baseline (2026-11-03, corpus-only restored; 28 documents, 785 chunks, index `20910f0964df`, dense `58ded7342e4c66fe`): BM25 8/11, BM25 plus lexicon 10/11, dense 8/11, hybrid **11/11** with MRR 0.56, abstention 3/4, two false refusals and 100% citation resolution; reference 2/2, statistics 2/2, jurisdiction 3/3 and national 2/2. Two larger variants were measured and rejected: 287 documents with cards and notes (hybrid 9/11, abstention 2/4) and 147 documents with cards only (hybrid 11/11, abstention 2/4). Adding broad external evidence without an abstention-aware gate removed two correct refusals, so cards and notes remain unindexed in that experiment; the two-index architecture later moved them to a separate external store (see knowledge-policy.md §6).
- Baseline (2026-11-03, card era adopted; 36 indexed documents — 28 corpus documents plus 8 web cards — 849 chunks, index `5135e00cfa3d`, dense `56b9551d4b080bc3`): BM25 8/11, BM25 plus lexicon 10/11, dense 8/11, hybrid **11/11** with MRR 0.56, abstention 3/4, two false refusals and 100% citation resolution; reference 2/2, statistics 2/2, jurisdiction 3/3 and national 2/2. Two questions were fixed without touching their anchors: Q-E01 through one active synonym group (起止日期 → 休渔时间) and Q-M10 by asking the concrete permit-application question the row was testing; the old phrasing named no operation type and could not be answered. The eight cards add species taxonomy, gear classification, warning-signal definitions and ocean-colour product descriptions. Q-E08 and Q-M09 remain parked because the MUR/OLCI product pages are JavaScript applications; a later batch needs static official documents. This 36-document card-era index was superseded by the two-index architecture; the adopted corpus index is back to 28 documents.
- Baseline (2026-11-03, after removing the nine dead entries; 28 public sources, 785 chunks, index `20910f0964df`, dense `58ded7342e4c66fe`): BM25 7/11, BM25 plus lexicon 8/11, dense 7/11, hybrid 9/11 with MRR 0.42, abstention 3/4, three false refusals and 100% citation resolution. Hybrid loses one question (Q-M10, anchored on `POL-STD-010` article 28) after the smaller index changes the ranking; the deletion was ordered for scope reasons, so the regression is published rather than reverted, and a retrieval follow-up is recorded. Reference 4/4, statistics 2/2, jurisdiction 3/3 and national 2/2 are unchanged.
- Baseline (2026-11-02, after dropping the six fishery-economy bulletins; 31 public sources, 846 chunks, index `2ad41cc64de3`, dense `dd318a16c295a32f`): hybrid holds 10/11 with MRR 0.44, abstention 3/4, three false refusals and 100% citation resolution. The comparison arms move slightly with the smaller corpus: BM25 6/11, BM25 plus lexicon 7/11, dense 7/11. The capture series now comes from the nine fishery yearbooks plus the China Statistical Yearbook, and the statistics section stays at 2/2.
- Baseline (2026-11-02, after removing the two out-of-scope documents; 37 public sources, 894 chunks, index `a28bbbf43a22`, dense `273e42c147570649`): every arm is unchanged from the thirty-eight-document baseline — BM25 6/11, BM25 plus lexicon 7/11, dense 7/11, hybrid 10/11 with MRR 0.44, abstention 3/4, two false refusals and 100% citation resolution. Removing the ranch and breeding material cost two chunks and no metric.
- Baseline (2026-11-02, after admitting the five enforcement, catalogue and operations texts; 38 public sources, 896 chunks, index `499b420f49b0`, dense `af4b31ca3f941169`): hybrid holds at 10/11 with MRR 0.44, abstention 3/4, two false refusals and 100% citation resolution. The comparison arms move further under the larger corpus: BM25 6/11 (was 7/11), BM25 plus lexicon 7/11 (was 8/11), dense 7/11 with MRR 0.30 and three false refusals. The dilution from 102 new chunks is published as measured; the adopted arm keeps its recall and abstention, and its MRR moves by 0.01.
- Baseline (2026-11-02, after admitting the four national texts; 33 public sources, 794 chunks, index `cd97744aa292`, dense `f15c73a5996702f5`): hybrid holds at 10/11 with MRR 0.45, abstention 3/4, two false refusals and 100% citation resolution. The comparison arms move under the larger corpus: BM25 7/11 (was 8/11), BM25 plus lexicon 8/11 (was 9/11), dense 8/11 with MRR 0.32 (was 0.37) and three false refusals. The one-anchor drop in the BM25 arms is the expected dilution from 121 new chunks; the adopted arm is hybrid, so the batch is kept and the comparison numbers are published as they are rather than smoothed.

| Arm | Recall@5 | MRR | Abstention | False refusals | P95 |
|---|---|---|---|---|---|
| BM25 | 17/19 | 0.64 | 7/8 | 2 | — |
| BM25 + lexicon | 19/19 | 0.69 | 7/8 | 1 | — |
| Dense (bge-small-zh) | 15/19 | 0.55 | 7/8 | 2 | 20 ms |
| **Hybrid (adopted)** | **19/19** | **0.68** | **7/8** | **1** | **20 ms** |
| Hybrid + LLM (`--llm`) | 19/19 | 0.68 | **8/8** | **0** | 22 ms |

The LLM row also scores answer correctness 0.76, completeness 0.66 and faithfulness 0.94 with the model judge; these are model-assisted scores, not human review.

Human review override: `scs-fkb eval --llm --review-template <path>` writes a per-question YAML template pre-filled with the model scores. `scs-fkb eval --llm --review <path>` applies the reviewer's correctness/completeness/faithfulness values per question and marks those rows `source: human`. Until a review file is applied, every score stays model-assisted.

Extractive faithfulness applies only to the deterministic extractive answers; it is not a quality metric for generated answers, which are scored by the model judge.

Adopted configuration (2026-11-04, updated by P09-EVAL-130): the reviewed set has 48 questions — 31 anchors, 11 abstention tests, 2 CWP reference questions, 2 statistics questions and 2 deferred web questions, split into 33 dev and 15 test. The corpus store decides answerability; the external store is a separate index and never participates in corpus abstention.

### Split baseline (2026-11-04)

| Split | Arm | Anchors | Abstention | MRR | Gold coverage |
|---|---|---:|---:|---:|---:|
| dev | hybrid | 19/19 | 7/8 | 0.6816 | 10/38 |
| dev | hybrid + LLM | 19/19 | 8/8 | 0.6816 | 15/38 |
| test | hybrid | 12/12 | 1/3 | 0.8542 | 2/22 |
| test | hybrid + LLM | 12/12 | 3/3 | 0.8542 | 10/22 |

LLM judge: dev correctness/completeness/faithfulness **0.7605/0.6605/0.9421**; test **0.7125/0.7083/0.8958**. The test split is a baseline, not a gate: it is not used for tuning, and a test-driven change must first become a dev question. The 0.6886 MRR sometimes quoted for the dev set is the BM25-plus-lexicon arm; hybrid is 0.6816.

- Statistics channel (2026-11-01): the two statistical questions are scored separately. Q-E06 runs 南海区海洋捕捞产量历年趋势 and expects the sea-area production series; Q-M05 runs 2019年南海区拖网渔船数量 and expects vessel counts. Both return rows with edition and table citations (2/2). The channel also states the two gaps: production has no operation-type dimension and vessel counts have no sea-area dimension.
- Reference collections (2026-11-03): two questions are scored outside the main index. Q-E05 and Q-M04 use the CWP definition collection and both return the expected passage (2/2). Q-E08 and Q-M09 were answered by the product documents, which were removed on 2026-11-03; they are parked in the `web` queue and will be restored when the cached card layer lands. The interim reference rate is therefore 100% over two questions, not comparable with the earlier 4/4 over four.
- Policy collection (2026-11-02): the crew-management rule `POL-CREW-055` joined the policy collection and answers the minimum-manning question; the channel still requires one of its cues before it fires, so an unrelated question does not reach these documents.
- Abstention denominator: the reviewed set has eleven out-of-scope tests (Q-E07, Q-E11, Q-M02, Q-M06, Q-M07, Q-M08, Q-M11, Q-M18, Q-C04, Q-O04, Q-T03); under the extractive gate seven of the eight dev tests abstain and Q-E07 is the known answered dev test, while the test split abstains 1/3; under `--llm` both splits abstain 8/8 and 3/3.
- Answer assembly (2026-11-02): when a question asks for a period and not for an implementation date, the extractive answer searches every retrieved hit for a sentence carrying a date range and, if found, cites it first. Q-E01 now leads with the South China Sea clause from [POL-CLOS-015 §三、休渔时间] instead of the implementation date in §四; the retrieval, reference, statistics and abstention metrics are unchanged.
- National section (2026-11-02): two questions exercise the national-first ordering. J4 2026年海洋伏季休渔执法行动由哪些部门开展、重点任务是什么？ expects `POL-ENF-068` and J5 远洋渔船标准化船型参数系列表（2024年版）有哪些船型和参数？ expects `STD-YY-071`. The section reports 2/2 separately; like the jurisdiction questions it is same-set calibration, not a held-out split.
- Jurisdiction section (2026-11-02): three province questions are scored separately from the main arms: J1 海南省2026年伏季休渔的时间和海域是什么？ expecting `POL-HN-059`, J2 广西2026年海洋伏季休渔的时间与要求是什么？ expecting `POL-GX-060`, and J3 汕头市2026年海洋伏季休渔有哪些管理要求？ expecting `POL-GD-061`. The section exercises the province-first re-ranking and the answer lead, reports 3/3, and is same-set calibration rather than a held-out split.
- Related: [evaluation questions](questions.md), [project plan](plan.md), [data policy](data-policy.md).

## 1. Purpose

Evaluation answers three questions:

1. Does retrieval return the right evidence?
2. Do answers cite that evidence correctly and avoid fabrication?
3. Does the system abstain when the corpus cannot support an answer?

Human review is authoritative for answer correctness. Automated metrics are supporting evidence, not a substitute for expert review.

## 2. Question set

The reviewed set contains 48 questions across four personas (captain/crew, owner/operator, enforcement and extension): 33 dev and 15 test. It contains 31 anchor questions, 11 abstention tests, 2 CWP reference questions, 2 statistics questions and 2 deferred web questions (Q-E08, Q-M09). Gold answer points and the `meta` persona/split mapping are in `configs/eval.yaml`; the project owner approved the 33-question dev set on 2026-11-04, and P09-EVAL-130 added the 15-question test split with the same evidence discipline. Test is report-only; a test finding must first become a new dev question before it can drive a product change.

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

The instrument scores anchors, not answers: a question counts as retrieved when a top-5 chunk matches one of its gold anchors in `configs/eval.yaml` (document plus section prefix, or document plus page). Answer correctness, faithfulness and completeness still need reviewed gold answers and per-answer scoring; the deterministic run scores extractive faithfulness (answer sentences must come from cited chunks) and citation coverage, while the `--llm` run uses the model judge for correctness, completeness and faithfulness. Under the deterministic gate Q-E12 is refused although its anchor is retrieved, and Q-E07 is answered although no registered source covers historical fishing seasons; under `--llm` both are corrected (Q-E12 answers, Q-E07 abstains).

## 4. Protocol

1. **Split the set:** dev 33 (existing) and test 15 (P09-EVAL-130). Test is report-only and is not used for tuning; a test-driven change must first be added as a dev question.
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

## Retrieval tuning review (2026-11-03)

Q-M10 stayed the only hybrid miss after the corpus was pruned. The pipeline exposes four levers, and each was measured against the eleven anchored questions:

| Setting | Result |
|---|---|
| title_boost 0.0 / 0.5 / 1.0 / 2.0, BM25:dense 2:1, fusion_k 60 | 8 / 9 / 9 / 9 of 11 |
| BM25:dense 1:1, title_boost 1.0 | 9 of 11 |
| BM25:dense 1:2, title_boost 1.0 | 8 of 11 |
| lexicon additions 准入→申请/许可, 监管→监督检查, 作业规范→作业类型/作业方式 | 8 of 11 |

The gold articles (POL-STD-010 第二十八条 and POL-LAW-009 第三十五条) never entered the top five under any tested setting at the time of this review. Q-M10 was then a generic question ("某类作业规范的准入条件与监管要求") mapped to a specific application-materials article, so parameter tuning could not separate that article from the many documents that mention permits. This review is kept as history: the final fix was the Q-M10 rewrite, and the adopted baseline now retrieves 11/11. The parameters stay at title_boost 1.0 and BM25:dense 2:1, and the 28-document corpus index remains the adopted one; cards and notes live in the separate external store.

## Coverage-check modes and calibration (2026-11-05)

The deterministic coverage check supports four modes:

| Mode | Rule |
|---|---|
| `all` | every check term occurs in one cited sentence (default) |
| `any` | at least one check term occurs in one cited sentence |
| `section` | every check term occurs somewhere in the cited sentences that share one `doc`/`page`/`section` |
| `document` | every check term occurs somewhere in the cited sentences that share one document |

`section` and `document` do not weaken `all`: `all` remains the default and still requires one sentence. `section` is for gold points whose source section legitimately states the point across several clauses; `document` is for a compound point whose clauses sit in different sections of one regulation. Both still require every term and a citation for every contributing sentence.

The 60-point audit reviewed the check terms against the anchor text and set `section` for 17 points. Seven check-term sets were replaced with source-exact wording (`原证`→`原渔业捕捞许可证`, `未变更`→`未发生变更`, `2021年`→`2021`, `按人`→`以人计罚`, `20万元`→`二十万元`, `200万元`→`二百万元`, `2828.1`→`2828`). Three formatting cases (full-width `２８２８`, `３ 艘` and the spaced `01·yn· W`) are handled by NFKC and whitespace folding rather than term changes.

P09-EVAL-135 resolved the five anchor gaps found by the audit:

- **Q-E10 p1**: no registered text contains `更严格`; the point now states only the supported clause (附件1/2). The removed unsupported clause is recorded in the private audit.
- **Q-M03 p1**: added `POL-STD-010` §第五十三条, where the warning/责令改正/1000元 wording actually sits.
- **Q-M12 p0**: added §第二十八条 for `作业事由`; the point spans §二十六 and §二十八 of one regulation, so it uses `document`.
- **Q-M17 p1**: added §第六条 and §第二十条; `周期` was replaced by the source term `营运检验` and the point uses `document`.
- **Q-O03 p1**: anchors are now §第四条, §第六条 and §第二十条; it uses `document`.

No question, point count (60), anchor count (31), abstention count (11), split or test membership changed. Private audit: `runs/P09-EVAL-135/audit.md`.

---

## Evaluation v2 (2026-11-06)

> **中文摘要**：本文件定义 120 题 v2 评测集和确定性指标。80 道 dev 题来自 80 条已批准事实，30 道 test 题来自草稿条款事实，10 道 test 题为拒答/澄清题。指标名称与 RAGAS 兼容，但不使用 LLM 评判；test 只报告、不用于调参。回归门禁要求 dev 正确率 ≥0.85、引用解析率 ≥0.99、上下文召回 ≥0.80、拒答准确率 ≥0.90。草稿题和合成题不是人工金标，报告中必须标注。

## 1. Question mix

| Split | Count | Source | Review status | Use |
|---|---:|---|---|---|
| dev | 80 | 80 approved facts | reviewed | Gate and regression |
| test | 30 | 30 draft provision facts | draft | Report only |
| test | 10 | abstention/placeholder cases | reviewed | Abstention gate |
| **total** | **120** | | | |

The set is generated deterministically by `scripts/build_eval_v2.py` from
`configs/facts/`. IDs are stable (`EV2-001` … `EV2-120`), and every expected
evidence doc/section must resolve to `configs/corpus.yaml`. The v1
`configs/eval.yaml` is not modified.

The 30 draft questions and the 10 abstention cases are test-only. The test split
is never used to tune retrieval, prompts or thresholds. Draft questions are not
human gold; their metrics are reported separately.

## 2. Metrics

The names follow the RAGAS vocabulary, but the implementation is deterministic
and does not call an LLM judge:

| Metric | Definition |
|---|---|
| `faithfulness` | Fraction of answer sentences carrying a resolvable citation; an abstention scores 1.0 |
| `answer_relevancy` | Character-bigram overlap between question and answer; abstention is scored against the expected abstention |
| `context_precision` | Fraction of cited documents that are in the expected evidence set |
| `context_recall` | Fraction of expected evidence documents present in the citations |
| `answer_correctness` | Max of expected-term coverage and character-bigram recall against the gold fact value; abstention must match |
| `citation_resolution` | Every citation has a doc id and a page/section/url; non-abstained answers need at least one citation |
| `abstention_accuracy` | Fraction of expected-abstention questions that actually abstain |

A per-question row also carries `latency_ms`, `mode`, `reason`, `error` and the
full answer/citation payload. `error` is recorded per question and never hidden.

## 3. Gate

`scripts/eval_v2.py` runs the service with `web=off` and enforces:

- dev `answer_correctness` ≥ 0.85
- dev `citation_resolution` ≥ 0.99
- dev `context_recall` ≥ 0.80
- overall `abstention_accuracy` ≥ 0.90

The test split is reported but not gated for correctness. A failing gate writes
the report and exits non-zero; the failure text is copied into the report.

## 4. Current result

The 2026-11-06 run:

| Group | Questions | Correctness | Citation | Context recall | Abstention |
|---|---:|---:|---:|---:|---:|
| dev | 80 | 0.8945 | 1.0000 | 0.9875 | — |
| test | 40 | 0.6161 | 1.0000 | 0.9500 | 0.9000 |
| overall | 120 | 0.8017 | 1.0000 | 0.9667 | 0.9000 |

The gate passes. The test correctness improved from 0.5820 before the 2026-11-06 review to
0.6189 after the 20 provision promotions, to 0.6319 after the seven-source
term batch, to 0.6310 after the third term batch, and to 0.6161 after the fourth
term batch (report-only; the dev gate held). It remains lower than dev because 30 test questions are derived from
draft section-level facts, not human gold answers. The report lists the failing rows individually.

## 5. Limitations

- No LLM judge; the metrics are deterministic proxies, not a semantic grader.
- 30 test questions are draft/synthetic; the 10 abstention cases are reviewed
  but intentionally unanswerable.
- The dev set is derived from the approved fact layer, so it measures fact
  coverage and citation behavior more than open-ended reading comprehension.
- Web evidence is disabled in this run; the web label path is covered by service
  tests, not by this metric set.

## 6. Reproduce

```bash
SCS_FKB_DATA_ROOT=... SCS_FKB_RUN_ROOT=... \
  PYTHONPATH=src python scripts/eval_v2.py
```

Outputs: `$SCS_FKB_RUN_ROOT/P10-EVAL-145/metrics.json` and `report.md`.

---

## Acceptance instrument (2026-11-07)

> **中文摘要**：新增 512 题私有验收工装：题目、判分要点与文档映射只存本地数据根，公开仓库只有
> 判分代码、阈值与协议。基线（2026-11-07，42 文档 / 1,014 chunks）测得可答率 44.5%、
> 要点覆盖率 0.167、引用准确率 0.166、误答率 0.314、拒答渠道率 0.029、时效声明率 0.070、
> 口径正确率 0.026，六项均未达协议通过线。差距集中在缺失语料（325/512 题引用未入库文档）、
> 结论式作答与拒答渠道；本工装只做度量，不参与产品路径。

### 1. Instrument

The acceptance workbook is a private instrument of 512 colloquial questions about
South China Sea nearshore fishing, each with required points, numeric anchors,
citation requirements and a graded answerability label. It is imported by
`scripts/import_eval_xlsx.py` into `$SCS_FKB_DATA_ROOT/eval/acceptance/` as
`dataset.jsonl` plus `manifest.json`; the manifest records the source digest and
the split seed, and a rerun is byte-identical.

| Layer | Value |
|---|---|
| Questions | 512 |
| Answerability | 388 answerable, 54 partially answerable, 70 refusal tests |
| Dimensions | 341 single fact, 64 multi-hop, 57 time conflict, 50 numeric |
| Domains | 17 |
| Splits | 256 dev, 256 holdout (`sha1(id + seed)`, fixed seed) |

The document map (`doc-map.yaml`, private) resolves the 77 instrument document
ids to repository documents: **21 full, 10 partial, 46 missing**. **325 of 512
questions reference at least one document that is not in the corpus**, which is
the largest single gap measured here.

### 2. Metrics

`src/scs_fkb/eval_accept/` scores every answer deterministically. Metric names
and pass lines mirror the instrument protocol; the thresholds live in
`configs/eval-accept.yaml`. Domain concepts come from `configs/terms.yaml` plus a
private `domain-terms.yaml` stored next to the dataset.

| Metric | Definition | Pass line |
|---|---|---|
| Point coverage | Hits over judgeable required points, averaged per answerable question. A point is judgeable when it carries a numeric, quoted or document-number anchor, or up to three domain concepts; other points are `needs_review` and excluded, and the judgeable share is reported. | ≥ 0.80 |
| Citation accuracy | Cited document maps to one of the question's required documents, and the cited clause matches the instrument's location label (≥ 3 shared characters) or carries one of the question's anchors. | ≥ 0.90 |
| Misanswer rate | Refusal-test questions answered without a refusal statement and a channel; unjudgeable rows are not counted as passes. | ≤ 0.10 |
| Refusal-with-channel rate | Refusal tests abstained or refused explicitly, with a handling or consultation channel. | ≥ 0.90 |
| As-of declaration rate | Time-conflict questions whose answer names the governing version (year or document number). | ≥ 0.90 |
| Basis accuracy | Numeric questions whose answer states the required value with a basis cue (national/sea-area, annual/per-trip, table or clause). | ≥ 0.85 |
| Latency | Mean and P95 answer latency. | recorded |

A per-question band (0 / 0.5 / 1) follows the protocol: a refusal test scores 0
when it answers with an entity claim and 1 only when it refuses with a channel;
an answerable question scores 1 only with full point coverage and a located
citation, and time-conflict answers without an as-of statement score 0.

### 3. Baseline (2026-11-07)

Corpus 42 documents / 1,014 chunks (index `d007984ae168`), `BAAI/bge-small-zh-v1.5`,
web off, extractive arm.

| Metric | Value | Rows | Pass line | Passed |
|---|---:|---:|---:|---|
| Point coverage | 0.1675 | 385 | 0.80 | no |
| Citation accuracy | 0.1659 | 205 | 0.90 | no |
| Misanswer rate | 0.3143 | 70 | 0.10 | no |
| Refusal-with-channel rate | 0.0286 | 70 | 0.90 | no |
| As-of declaration rate | 0.0702 | 57 | 0.90 | no |
| Basis accuracy | 0.0263 | 19 | 0.85 | no |
| Answer rate | 0.4453 | 512 | — | — |
| Latency mean / P95 | 17.3 ms / 22 ms | 512 | — | — |

Domain contrast follows the corpus gap: 捕捞许可 0.403 and 捕捞日志与渔业统计 0.309
point coverage against 海洋灾害与生态, 渔情与遥感 and 保护物种 near zero, where the
governing documents are not indexed. 553 of 1,117 required points are judgeable
(49.5%); 373 questions carry at least one review-needed point. Only 19 numeric
questions carry a numeric anchor in the instrument, so basis accuracy covers a
narrow slice.

The gate therefore fails on all six lines. This is the pre-change baseline; the
report is `$SCS_FKB_RUN_ROOT/<task>/baseline.md` with per-question rows in
`rows.csv`, and it is not used to tune retrieval before the corpus and answer
contract work lands.

### 4. Limitations

- The scorer is deterministic and rule-based. It rewards anchors and citations,
  not semantic completeness; points without anchors are reported, never guessed.
- Location matching is a proxy: the instrument states locations as topic labels,
  so a cited clause counts as located when it matches the label or carries the
  question's anchors.
- The holdout split is reported but scored with the same rules; no human review
  of gold answers has been applied to the instrument yet, and the reference
  answers remain review starters rather than gold.
- Web evidence is disabled in every reported run.

### 5. Reproduce

```bash
# import (private workbook; output stays under the local data root)
python scripts/import_eval_xlsx.py --xlsx <workbook> \
  --out-dir "$SCS_FKB_DATA_ROOT/eval/acceptance"

# score (add --split dev|holdout, --dimension, --persona, --limit to narrow)
SCS_FKB_DATA_ROOT=... SCS_FKB_RUN_ROOT=... PYTHONPATH=src \
  python scripts/eval_accept.py --allow-fail
```

The command exits non-zero when a pass line is missed; `--allow-fail` is used
for baselines so the report is still written. `--llm` switches to the optional
LLM arm and falls back to the extractive arm with an explicit error when the
endpoint is not configured.

### 6. Calibrated scoring (2026-11-07)

> **中文摘要**：本轮只校准判分，不改作答与语料。引用定位改为"主题词覆盖 + 页码/表号"匹配；
> 无字面要点的要点按"要素类型"规则评分（时间、层级、材料、罚则、比例等）；113 个要点用
> 原文/参考答案核过的短词覆盖。可判要点从 553/1,117 升到 849/1,117（76.0%）。
> 校准后基线：要点覆盖 0.1684、引用准确 0.3810（旧规则 0.1753 / 0.1714），其余五项不变。

- Location matching: the instrument location is split into topic tokens after
  removing document numbers and generic suffixes; a citation is located when its
  section, snippet or cited sentence covers at least half of the tokens, or when
  a page/table label matches the citation page or snippet. LCS and required-anchor
  fallbacks remain; unjudgeable locations stay in a separate `unmatched` bucket
  (130 citations in the 512 run).
- Typed rules: points that name an element without a literal anchor are scored by
  the element type (time range, approval level, materials, penalty, ratio, list,
  channel, record, inspection, certificate, condition, scope, relief, category,
  measure, comparison, forecast, method, definition, sampling, identification,
  responsibility, frequency). Rules run only on cited text.
- Grounded overrides: 113 points received 2–4 character terms checked against the
  cited clause or the reference answer; 2-character terms require document
  frequency ≤ 8. The override file stays private with the dataset.
- Point classes: 553 anchored, 183 typed-rule, 113 override, **849 judgeable
  (76.0%)**, 268 needs review. The remaining points are negations and case
  judgements with no deterministic anchor; coverage bounds with them are 0.109
  (all miss) to 0.349 (all hit).
- Calibrated baseline (same answers and corpus): point coverage **0.1684**,
  citation accuracy **0.3810**, misanswer 0.2571, refusal-with-channel 0.5857,
  as-of 0.3509, basis 0.0263. Downstream tasks compare against these numbers; the
  old 0.1753 / 0.1714 pair stays as history.

### 7. LLM composition arm (2026-11-08)

> **中文摘要**：新增可选 LLM 组合作答臂（默认关闭）。检索 8 条证据后由模型按
> "结论先行 + 逐句引用"作答，再硬校验：引用可解析、数字能在被引证据中找到、
> 核验器确认结论有证据支持。任一失败先修复一次，再失败就转缺口答复；模型不可用时
> 回退抽句式。70 道应拒答题仍走确定性路径。

- Default remains the extractive arm; `SCS_FKB_ANSWER_MODE=llm` enables the arm.
- Checks: citation resolution, number grounding in the cited evidence, and a
  verifier call; a single repair pass, then a gap answer.
- The arm applies to 可答/部分可答 rows in the acceptance runner
  (`--llm-answerability`), while 应拒答 rows stay deterministic so misanswer is
  not traded for coverage.
- Replies are cached under the data root by prompt version, question, evidence
  and model, so re-runs are free.

#### First full arm run (2026-11-08)

| Metric | Extractive | LLM arm |
|---|---:|---:|
| Answered | 231 | 457 |
| Point coverage | 0.1684 | 0.3395 |
| Citation accuracy | 0.4048 | 0.2821 |
| As-of declaration | 0.5439 | 0.8070 |
| Misanswer (refusal) | 0.2571 | 0.2571 |
| Mean latency | 22 ms | 30.4 s |

The arm doubles coverage and lifts as-of declarations, but citation accuracy falls
because cited sections rarely repeat the instrument's topic labels, and latency is
endpoint-bound. Coverage reaches 49% of the 0.687 corpus ceiling (583 reachable
points of 849), so the 0.80 line needs both a higher ceiling and more per-answer
completeness.

### 8. Coverage denominator and evidence audit (2026-11-08)

> **中文摘要**：849 个可判要点里有 122 个属于 70 道应拒答题——这些题按协议必须拒答，
> 其要点永远不可能被覆盖，因此现行要点覆盖率分母被低估。按"应答题"分母（727 点），
> 当前上限是 0.795，而不是 0.681。92 道"期望文档不在库"的题逐题审计后仅 15 道可由
> 现有索引回答（26 点），映射后上限 0.831；当前实际覆盖 0.396，要达到 0.80 需要覆盖
> 96% 的可达要点。

- The scorer's point-coverage denominator includes refusal-points (122 of 849).
  Coverage will be reported over answerable points (727) in the next scorer change,
  with the all-points number kept for continuity.
- Evidence audit: 92 unreachable answerable questions; 15 mappable to existing
  clauses (5 full, 10 partial, 26 points); 77 have no supporting clause. Model
  judgements need a 20% spot-check before mapping.
- Ceiling (answerable denominator): 0.795 current, 0.831 with mapping. Current
  coverage 0.396; the gap needs answer completeness, not just corpus growth.

### 9. Answerable coverage denominator and mappings (2026-11-08)

> **中文摘要**：要点覆盖率分母改为"应答题"（可答 + 部分可答，727 点），849 点旧口径
> 保留为 `point_coverage_all`。13 条审计映射经 20% 抽检后应用（2 条被拒），可达要点
> 从 578 升到 643，上限 0.8845。当前覆盖 0.3819（278 点），达到 0.80 需要覆盖 90.5%
> 的可达要点。

- Coverage is measured over answerable questions; refusal points (122) are excluded
  because those questions must abstain. Both figures are reported.
- 15 audited mappings: 13 applied as partial, 2 rejected after reading the clause
  (the sentence question cited a case report; the hypoxia question cited closure
  dates). Each map entry carries the audit question, document and section.
- Reachable answerable points 578 → 643; ceiling 0.795 → 0.8845. Current coverage
  0.3819 (278 points), i.e. 43% of reachable points; the 0.80 line needs 90.5%.

### 10. Three reachable lines closed; basis re-scoped (2026-11-08)

> **中文摘要**：证据充分性判定器把"只沾边"的确定性回答改为拒答，误答率 0.2571 → 0.0571；
> 所有中止/澄清都带渠道，渠道率 0.9429；时效声明扩展到中止与澄清并修正日期格式，0.9123。
> 口径线（basis 0.0526）不在契约层可解：19 道数值题要求答案包含全部数值锚点，属于数值
> 召回/作答完整性，移入 P4。

- Deterministic answers now pass an evidence-sufficiency judge; `partial`/`none`
  abstain with a gap. Misanswer 0.2571 → 0.0571.
- Channels are attached to clarify, weak-evidence and refusal answers; refusal
  channel 0.5857 → 0.9429.
- As-of declarations cover abstains and clarify responses and use Chinese dates;
  0.8070 → 0.9123.
- Basis remains 0.0526 because the metric requires every rubric numeric anchor in
  the answer (17/19 answers omit at least one); it moves to the numeric-answer
  completeness work.


#### Sufficiency verifier flag

The runtime evidence-sufficiency judge is enabled with
`SCS_FKB_VERIFY_ANSWERS=on` for acceptance runs and production; it is off by
default so tests and offline use never call the model implicitly. With the flag
on, the 512 run reproduces misanswer 0.0571, refusal-with-channel 0.9429 and
as-of 0.9123.
