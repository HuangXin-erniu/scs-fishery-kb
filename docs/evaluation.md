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
| test | 40 | 0.5820 | 1.0000 | 0.9500 | 0.9000 |
| overall | 120 | 0.7903 | 1.0000 | 0.9750 | 0.9000 |

The gate passes. The lower test correctness is expected: 30 test questions are
derived from draft section-level facts, not human gold answers. The report lists
the failing rows individually.

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
