# Project Plan

> **中文摘要**：本文件把项目范围拆成 WP0–WP6 工作包、M0–M4 阶段、角色、质量门与风险。
> 里程碑是工作阶段，不是版本；项目不创建 tag 或 GitHub Release。
> 当前处于 M3（评测与服务原型）：77 个来源已登记、0 个开放候选；source schema v4 的权威/时效/许可/等级门禁与候选队列已接入 CI；42 份公开文档已索引（1014 块）；混合检索 19/19、拒答 8/11；48 题评测（33 dev + 15 test）与 38 点覆盖基线见 evaluation.md。
> P10 重构于 2026-11-06 启动：双平面证据、LlamaIndex + LanceDB + BGE、受控网络检索、流程/术语内化与 120 题验收；第一阶段 P10-GOV-136 已建立治理基线。M1/M2 已完成，WP6 在 P10 中实现。

- Status: active plan; WP1 is closed with 77 registered sources and no open candidates; WP2 indexes 67 public documents (2,797 chunks, index `ce3eeaf4c9b2`); WP3 and WP4 are implemented with hybrid retrieval and a dump answer arm; WP5 evaluation runs the frozen 512-question acceptance instrument, the 48-question reviewed set and the 60-item public regression set; WP6 is implemented with the `/v1` contract, the `/kb` layer and the feedback loop. P21 is the acceptance programme: indicators are published in [acceptance.md](acceptance.md). The P10 refactor is tracked in section 3a.
- No versioned releases are published. Milestones describe work stages, not release numbers.
- Architecture: [architecture.md](architecture.md); evaluation: [evaluation.md](evaluation.md); scope: [../PROJECT.md](../PROJECT.md).
- P26 (2026-11-12) starts the second-stage refactor: a standard RAG answer pipeline, a dual-track industry-standard evaluation, a semi-automatic update loop and crew-facing practical sources; see section 3b and ADR 0009–0013.

## 1. Purpose

This plan turns the project scope into work packages, deliverables, milestones and acceptance criteria. It is the reference for what is built, in what order, and how completion is judged.

## 2. Scope summary

The project builds a governed knowledge-layer corpus of nearshore South China Sea fishing-vessel and fishery-condition material, a hybrid retrieval pipeline, evidence-grounded answers with citations and abstention, and a reproducible evaluation. It does not train forecast models, publish raw environmental data or full vessel tracks, or integrate downstream platform data.

Detailed scope and non-goals are in [../PROJECT.md](../PROJECT.md). The architecture is in [architecture.md](architecture.md).

## 3. Work packages

| WP | Name | Deliverables | Acceptance |
|---|---|---|---|
| WP0 | Framework and governance | Scope, architecture, plan, evaluation, corpus register, questions, public tooling and CI | Documents reviewed; CI passes |
| WP1 | Corpus acquisition and registration | Policy documents plus nine yearbook editions; licence, sensitivity, version and hash recorded | No unknown source ingested; acquisition path documented |
| WP2 | Ingestion and knowledge organisation | Parser, chunker, table/indicator extraction; processed records and manifest | Page/section/table anchors present; manifest reproducible |
| WP3 | Retrieval | BM25, dense retrieval, fusion, metadata/sensitivity filtering; retrieval report | Retrieval baseline measured on a reviewed subset |
| WP4 | Answer generation and evidence | Evidence-only prompt, citation validation, abstention | No fabricated citation; out-of-scope refusal works |
| WP5 | Evaluation | Reviewed question set; baselines; error analysis; evaluation report | Metrics and limitations reported |
| WP6 | Service and interface | CLI/HTTP query surface; `/v1` interface contract (`docs/interface.md`, `configs/interface.yaml`) | Contract reviewed; no data integration implemented |

P17 (2026-11-10) restored the controlled web-evidence layer, the weekly update loop, a worker-facing `/kb` layer with a public regression set, and versioned indexes with a retrieval gate; the 512 instrument and document map stayed frozen. WP0 is complete. WP1 is closed with 77 registered sources and no open candidates: 1 law, 22 regulations, 19 notices, 18 standards, 10 statistical yearbooks (nine fishery yearbook editions for data years 2017–2025 and the China Statistical Yearbook 2026), 3 data dictionaries, 1 operations reference, 2 fishery reports and 1 emergency plan. The 3,126-row core CSV is built locally and has passed source-hash and spot-value checks. Three coverage gaps remain documented: no port infrastructure table for data years 2018–2019, no marine vessel-length table for 2024, and a sampled data year 2025. The 2026-11-01 sufficiency review accepted the draft question set (ten answerable, six partial and eight abstention tests at that time); the reviewed 48-question set (33 dev + 15 test) remains the developer set, and the frozen 512-question instrument is the acceptance measure. WP2 indexes the 67 public documents into 2,797 chunks with section and page anchors; the index holds no internal source. The public regression set reports recall@5 0.8298 and MRR 0.7348 over 47 retrieval rows; the frozen 512 instrument reports coverage 0.8092, citation 0.9565, misanswer 0.0000 and refusal-with-channel 1.0000. The CWP reference collection answers Q-E05 and Q-M04 (2/2); Q-E08 and Q-M09 remain parked. P06 exposes the yearbook indicator table locally via `scs-fkb stats` (2/2). The register uses source schema v4 (`level`, `authority_tier`, `source_class`, `provenance`, `effective`, `quality`, `currency.cadence`, `license`, `sensitivity`, `lifecycle`, `retrieval`), enforced by `src/scs_fkb/registry.py`; 77 v4 entries are loaded; the original 63 v3 entries were normalised to v4 without changing ids or hashes. A curated watch list runs read-only; changed pages become candidate drafts under the run root and are never ingested automatically. `src/scs_fkb/candidates.py` validates the queue, and `scripts/check_sources.py` makes the review date, licence and tier a CI gate; the weekly cycle is in [operations.md](operations.md). P17 restored the watch/candidate tooling and the web-evidence layer (default off) in 2026-11-10. WP3, WP4 and WP6 are implemented; WP5 holds the frozen 512 instrument, the 48-question developer set and the 60-item public regression set; P21 converts them into acceptance evidence.

### SCS-FKB refactor programme (2026-11-06)

The project owner approved a deep refactor that keeps the source register, facts,
evaluation and public boundary, and replaces the orchestration and service layers.
The baseline is frozen at `main` `f038cbd`: 63 sources, 28 indexed documents,
785 chunks, index `20910f0964df`, 48 evaluation questions, 340 passing tests.
The paused B1 branch at `0841f56` is reference-only and was cancelled; it is not
merged.

| Phase | Scope | Exit condition |
|---|---|---|
| P10-GOV-136 | Source schema v4, provenance/effective/quality, RAG standard, ADRs, migration audit, technology spike | 63 sources load under v4; checks green |
| P10-ING-138 | Docling/trafilatura adapters, hierarchical chunking, snapshots and incremental manifest | 28 main documents rebuild with 0 lost anchors; 63 sources snapshotted; reference/statistics channels unchanged |
| P10-IDX-139 | LanceDB, BGE embedding/reranker, hybrid retrieval, router and filters | 48-question regression not below baseline; latency/RSS targets |
| P10-WEB-140 | SearXNG/DDG, allowlist, WebEvidence, TTL, trigger policy and promotion | 20 freshness questions; 0 non-allowlisted; no auto-ingest |
| P10-KB-142 | 15 playbooks, 150 terms, 200 facts, extraction/review, weekly loop | Validators green; weekly report reproducible |
| P10-ANS-143 | Answer composer/validator, FastAPI `/v1`, Web UI and feedback | 20 scenarios; citation resolution 100%; localhost service |
| P10-EVAL-145 | 120-question set, RAGAS-compatible metrics, regression gate, docs sync | Acceptance thresholds met; release gate clean |
| P10-REV-146 | Review 120 draft facts, 34 draft terms and 15 playbooks | 20 promoted; 34 terms kept draft; playbooks corrected |
| P10-WEB-147 | SearXNG local provider with DuckDuckGo fallback | 15/20 queries with evidence; 1 explicit failure |
| P10-IDX-148 | Reranker calibration on 31 reviewed anchors | Default off; no arm meets anchor+MRR+latency |
| P10-IDX-149 | Rebuild external fact/term store after review | 487 docs / 543 chunks; fact and term retrievable |
| P10-TERM-152 | Seven official term sources with A/B admission | 70 sources / 35 docs / 905 chunks; 123 approved terms |
| P10-TERM-154 | Batch 2: three new sources and two existing-source terms | 73 sources / 38 docs / 920 chunks; 128 approved terms |
| P10-TERM-155 | Batch 3: market, MSY and subsidy terms | 76 sources / 41 docs / 971 chunks; 133 approved terms |
| P10-TERM-157 | Batch 4: ocean product terms; metadata deferred | 77 sources / 42 docs / 1014 chunks; 136 approved terms |

P10-ING-138 (re-post of the originally scoped ingestion task) is implemented as
a parallel store: 63 sources are snapshotted, the 28 configured main documents
build into 745 parent and 785 child chunks with 0 lost page/section anchors, a
second run skips all 28, and a changed source rebuilds only itself. The live v1
store, index and answer path are unchanged; the 23 reference documents and 10
statistics sources keep their existing channels until the index task wires them
into the new store.

P10-IDX-139 is implemented as a parallel retrieval stack: the 785 v2 child
chunks are embedded into a LanceDB table (`23e933753e22`, 512 dims) in 98 s at
4.49 GB peak RSS. The no-rerank hybrid arm matches the v1 baseline (dev 19/19,
test 12/12, abstention 8/11, P95 16 ms); the optional BGE reranker improves MRR
but loses two anchors and raises P95 to 2.27 s, so it is off by default. The v1
answer path is not switched.

P10-WEB-140 is implemented as the ephemeral web plane: 20 freshness queries were
smoke-tested with 13 queries returning 32 allowlisted evidence records, 75
non-allowlisted results dropped and 5 provider failures recorded. TTLs are 7/30/
90/365 days by claim nature; promotion returns a candidate draft and writes
nothing.

P10-KB-142 is implemented: 15 approved playbooks with 32 fact-cited steps, 150
terms (116 approved, 34 draft), 200 facts (80 approved, 120 draft provision
facts), a playbook validator and a read-only weekly report. The checks are green
and the weekly report records 63 sources, 26 watch entries, 200 facts, 150 terms,
15 playbooks and 6 gaps.

P10-ANS-143 is implemented as a local service: 20 reviewed scenarios through the
real v2 stack produced 19 answers, 1 clarification, 19 cited answers and 16
expected-document hits, median 22 ms. The API exposes `/v1/query`,
`/v1/sources`, `/v1/playbooks`, `/v1/feedback` and health endpoints; the Web UI
is server-rendered and the v1 CLI/answer path is unchanged.

P10-EVAL-145 is implemented: the 120-question set has 80 dev reviewed facts, 30
draft test facts and 10 test abstention cases. The dev run scores 0.8945
correctness, 1.0000 citation resolution and 0.9875 context recall; overall
abstention is 0.9000. The gate passes; the test split scores 0.6161 correctness
(0.5820 before the review, 0.6189 after the provision review, 0.6319 after the
second term batch, 0.6310 after the third) and is report-only because its 30 fact
questions are drafts. This completes the
planned P10 phases; no tag or release is created.

P10-REV-146 reviewed the draft knowledge layer: 20 article-level provision facts
were promoted (facts now 100 approved / 100 draft), 34 terms stayed draft because
none occurs in the registered corpus, and six playbook statements were corrected.
The review is an AI-assisted first pass recorded in
[review-2026-11-06.md](review-2026-11-06.md); owner spot-check remains.

P10-IDX-149 rebuilt the separate external store after the review: 487 documents
and 543 chunks (100 approved facts, 116 approved terms, 119 cards, 140 notes and
12 FAQs), chunk index `0b1ecdf229fe` and dense index `6bdf2aad95935994`. A fact
query and a term query both return external records. The corpus store remains 28
documents / 785 chunks / `20910f0964df`.

P10-TERM-152 admitted seven official term sources through the candidate queue and
a staging A/B gate. The corpus is now 70 sources / 35 documents / 905 chunks
(index `4d94e7c7f27c`); v2 is 905 chunks (index `c25ddffea992`); v1 anchors remain
31/31, dev 19/19, test 12/12 and abstention 8/11; v2 dev correctness stays
0.8945 and citation 1.0000. Terms are 123 approved / 27 draft; the external store
is 494 documents / 550 chunks (index `9405a2f93585`). `POL-CODE-084` uses the
narrow 1100 notice after the 1562 page caused an out-of-scope loan answer.

P10-TERM-154 added three sources: POL-CONS-090 (过度捕捞), POL-MIN-091
(最小可捕规格) and INT-SUS-092 (兼捕); it also approved TERM-048 from
POL-SANWU-086 and TERM-088 (型宽) from POL-CODE-084. The first broad captures
were replaced by narrow pages after staging false answers, then the gate passed:
v1 31/31, dev 19/19, test 12/12, abstention 8/11; v2 dev 0.8945, test 0.6327,
overall 0.8072, citation 1.0000. The corpus is 73 sources / 38 documents / 920
chunks (`0a8d928f2ad2`, v2 `659a7a8c507e`); terms are 128 approved / 22 draft;
the external store is 499 documents / 555 chunks (`7c58c522ab5c`).

P10-TERM-155 approved five more terms: 数据共享 and 海温 from existing sources,
plus 渔获物上市交易, 最大可持续产量 and 休渔补贴 from new sources. The corpus is
76 sources / 41 documents / 971 chunks (`43491719734d`, v2 `7d372c2b5f47`);
v1 remains 31/31 and 8/11; v2 dev stays 0.8945, overall 0.8066, citation 1.0000.
Terms are 133 approved / 17 draft; the external store is 504 documents / 560 chunks (`c03a133b9f2e`).

P10-TERM-157 approved three ocean-product terms from POL-OCEAN-096:
叶绿素a浓度, 海面风场 and 有效波高. 数据元 and 元数据 stayed draft because
the 89-page GB/T 18391.3 candidate pulled generic metadata chunks into Q-M06 and
dropped v1 abstention to 7/11; it remains an open candidate. The corpus is now
77 sources / 42 documents / 1014 chunks (`f7a244373e77`, v2 `d007984ae168`);
v1 remains 31/31 and 8/11; v2 dev 0.8945, test 0.6161, overall 0.8017, citation
1.0000. Terms are 136 approved / 14 draft; the external store is 507 documents /
563 chunks (`458aad366fe1`).

The architecture decisions are [0005](adr/0005-two-plane-evidence.md),
[0006](adr/0006-llamaindex-lancedb-bge.md),
0007（已移除） and
[0008](adr/0008-playbooks-and-terms.md). The construction standard is
[rag-standard.md](rag-standard.md). Sources, data, indexes and run artifacts stay
outside the public tree; no tag or release is created.

### SCS-FKB second-stage refactor programme (2026-11-12)

The owner approved a second-stage refactor after the fourth holdout showed the
binding constraint is corpus coverage and the default clause-dump arm is not a
standard RAG pipeline. The 512 instrument, its labels, the source register and
the public/private boundary are kept; the answer path, the update loop, the
evaluation and the content mix change. The decisions are ADR
[0009](adr/0009-standard-rag-answer-pipeline.md),
[0010](adr/0010-dual-track-evaluation.md),
[0011](adr/0011-semi-automatic-update-loop.md),
[0012](adr/0012-practical-sources-and-freshness.md) and
[0013](adr/0013-source-schema-v5.md).

| Phase | Scope | Exit condition |
|---|---|---|
| Phase 0 | Baseline freeze, RAGAS isolation, Track B dataset skeleton, practical-source survey, ADRs | Baseline numbers/commands/commits recorded; RAGAS run works; dataset skeleton frozen; candidate survey written |
| Phase 1 | Standard RAG answer pipeline, reranker calibration, citation validator, semantic cache, API additions | Track B generation/citation targets met; Track A does not regress; tests green |
| Phase 2 | Source schema v5, semi-automatic update cycle, provisional tier, light structured internalisation | One real cycle completes; provisional to canonical review works; facts/cards/answers enter the draft queue |
| Phase 3 | Crew-facing practical sources, `/kb` task cards, PWA/offline, feedback-to-gap loop | At least 20 practical sources are retrievable; 20 crew scenarios work; feedback closes the loop |
| Phase 4 | Full Track B run, human spot check, docs and release gates | Dual-track report published; public tree and private gate clean; no tag or release |

The evaluation design keeps two tracks: Track A is the frozen 512 instrument
and the dump arm (internal regression and materials-review evidence); Track B is
the RAGAS, retrieval, citation, abstention and human spot-check suite (product
gate). The two numbers are never averaged. Track B targets and pass lines are
published only after the Phase 0 baseline.

**Phase 1 status (2026-11-12).** The standard RAG answer arm is the product
default: bounded evidence pack, structured JSON, citation/number/support
validation, optional self-check, semantic cache and a jurisdiction caveat when a
province is not named. The public retrieval gate is unchanged (recall@5 0.8864,
MRR 0.7848, nDCG@10 0.8107); the cross-encoder lowered all three on a 12-row
subset while raising p95 to 2.2 s, so it stays off by default. A one-row Track B
RAGAS smoke failed the targets (context recall 0.0000, answer correctness 0.1999)
because the question depended on a Guangdong rule that the retrieved pack did not
contain; the practical-coverage and province-slot work is carried forward.

**Phase 2 status (2026-11-12).** Source schema v5 is an additive upgrade with
provisional/canonical ingestion, licence evidence, TTL and practical tags; v3/v4
registers still load. The semi-automatic cycle (`scripts/update_cycle.py`) turns
a changed watch row into a provisional plan and never writes the canonical
register or index; promotion remains human-gated. Task cards (15 drafts) and
canonical answers (16 approved) are validated in CI. The Track B gate is not
armed; the next work is practical-source coverage and the full Track B run.

### Source gate and candidate queue (2026-11-04)

- Schema v3 adds `currency.cadence` with a per-cadence cap on `review_due - as_of` (monthly 60 days, quarterly 150, annual 400, semiannual 240, static 550). The 63 sources were migrated by class: normative `monthly`, standard `quarterly`, `official_statistics` `annual`, reference `semiannual`; hashes, dates, locations and statuses are unchanged.
- `license` and `sensitivity` are checked against the allowlist in `configs/schema.yaml`; tier and level must agree (C municipal only, D non-official only, A/B never municipal or non-official).
- `scripts/watch_sources.py --propose` writes proposals under the run root only. A proposal enters `configs/candidates.yaml` as `open`, is due after 90 days and expires after 180; `accepted` needs a registered `source_id`, `rejected` needs a note, and a duplicate URL is rejected.
- `scs-fkb sources check --today YYYY-MM-DD [--grace-days 30]` fails when an active source is past `review_due` plus grace, when a candidate is malformed or expired, or when an accepted candidate names a missing source. It runs in `make check` and CI with the real date; tests inject a fixed date. Nothing is downloaded, ingested or indexed by any of these commands.

## 4. Milestones

| Milestone | Content | Exit condition |
|---|---|---|
| M0 | Framework and public baseline | Scope, architecture, plan, evaluation, corpus register, questions and CI are published |
| M1 | Minimal pipeline | Two or three documents are parsed, indexed and answerable with citations |
| M2 | Retrieval baseline | BM25, dense and hybrid retrieval are compared on a reviewed subset |
| M3 | Evaluation and service prototype | Citation/answer metrics and an end-to-end CLI/HTTP demonstration are reported |
| M4 | Interface contract | The `/v1` contract is reviewed; no data integration is included |

Milestones do not create releases or tags. Completion is judged by the exit condition and the quality gates below. M1 and M2 are complete; the current phase is M3, with WP5 evaluation in progress on the 48-question set. WP6 is implemented in the P10 service task (P10-ANS-141).

## 5. Dependencies and sequence

```text
WP0 framework
  → WP1 corpus
    → WP2 ingestion
      → WP3 retrieval
        → WP4 answers
          → WP5 evaluation
            → WP6 service + interface contract
```

- WP1 depends on source owners and licence confirmation.
- WP2 depends on at least two public documents.
- WP3 and WP4 can iterate together after the first index exists.
- WP6 depends on a stable query path; the contract is defined after WP3/WP4 are demonstrable.

## 6. Roles

| Role | Responsibility |
|---|---|
| Project owner / decision-maker | Scope, priorities, decisions, review and acceptance |
| Maintainer / executor | Implementation, tests, documentation and evidence |
| Domain expert | Real questions, definitions, gold answers and answer review |
| Data owner | Source access, licence, sensitivity and permitted use |
| Downstream interface owner | Review of the `/v1` contract and integration boundary |

The project owner approves scope changes. The maintainer records evidence for every deliverable. Domain experts review the question set and answer quality. Data owners confirm source terms.

## 7. Schedule

A six-week working schedule is suggested; it can be compressed or extended.

| Week | Focus | Output |
|---|---|---|
| 1 | Framework and corpus discovery | Reviewed scope/architecture/plan; P1 source list |
| 2–3 | Ingestion and minimal retrieval | Processed corpus; first citations |
| 4 | Retrieval baseline | BM25/dense/hybrid comparison |
| 5 | Evaluation and service | Metrics report; CLI/HTTP prototype |
| 6 | Contract and review | `/v1` contract; final review |

Dates are not commitments. Milestone exit conditions and quality gates take precedence.

## 8. Quality gates

1. **Source gate:** licence and sensitivity known; unknown sources held; restricted sources local-only.
2. **Public-tree gate:** `scripts/check_public_tree.py` passes; no data, run artifacts, secrets or absolute paths.
3. **Citation gate:** every factual claim has a citation that resolves to a retrieved chunk.
4. **Evaluation gate:** reviewed questions, baseline comparison, error analysis and human review.
5. **CI gate:** `ruff check`, `ruff format --check`, `pytest` and the public-tree check pass.
6. **No-tag gate:** the repository has no Git tags; CI and the public-tree check fail on any tag.

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Source licences or sensitivity unclear | Cannot ingest or publish | Register every source; hold unknown values; keep restricted sources local |
| Scanned documents or complex tables | Extraction errors | Text-layer PDFs first; OCR optional; quarantine low-quality items; human spot checks |
| Evaluation set bias | Metrics look good but do not reflect use | Real questions; expert review; held-out set; human review authoritative |
| Scope expansion | Becomes a forecasting or platform project | Scope and non-goals in PROJECT.md; changes go through the owner |
| Local resource limits (8 GB) | Large models or parallel jobs are impractical | Hosted model endpoint; small local embeddings; batch processing; one active task |
| Interface drift | Downstream rework | `/v1` contract; additive fields; index version traceability |
| Missing corpus | The minimal pipeline cannot start | Owner provides two or three P1 public documents first |

## 10. Change control

- Scope changes, new data classes and new external dependencies require a project decision.
- The public tree must remain free of data, run artifacts, secrets and internal identifiers.
- A change that affects the `/v1` contract requires review with the downstream interface owner.
- No release or tag is created as part of this plan. CI fetches tags and rejects any tag; the repository is expected to have none.

## 11. Out of scope

- Fishery-forecasting model training, inference or products.
- Raw environmental grids, reanalysis data or full AIS/VMS tracks.
- A production multi-tenant platform.
- Downstream data integration.
- Publishing restricted or unlicensed data.

## 12. References

- [Project scope](../PROJECT.md)
- [Architecture](architecture.md)
- [Evaluation](evaluation.md)
- [Corpus inventory](corpus.md)
- [Evaluation questions](questions.md)
- [Data policy](data-policy.md)
- [Corpus register](../configs/corpus.yaml)
- [Data schema](../configs/schema.yaml)

**Phase 3 status (2026-11-12).** The crew knowledge station now exposes task
cards and canonical answers, a PWA/offline shell and task/answer feedback; the
candidate review tool writes provisional review packages without network or
register writes. Practical-source admission itself remains human-gated: the 30
surveyed candidates are still open, and the triage report finds that all 30 need
a document-level hash, an explicit licence/sensitivity decision and a parseable
document URL before a provisional review package can be built. No candidate was
auto-ingested. The
province-slot fix is a national-first evidence preference when no province is
named; it reduces, but does not remove, the coverage gap exposed by the Track B
smoke.
