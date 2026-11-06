# Project Plan

> **中文摘要**：本文件把项目范围拆成 WP0–WP6 工作包、M0–M4 阶段、角色、质量门与风险。
> 里程碑是工作阶段，不是版本；项目不创建 tag 或 GitHub Release。
> 当前处于 M3（评测与服务原型）：63 个来源已登记、0 个开放候选；source schema v4 的权威/时效/许可/等级门禁与候选队列已接入 CI；28 份公开文档已索引（785 块）；混合检索 19/19、拒答 7/8；48 题评测（33 dev + 15 test）与 38 点覆盖基线见 evaluation.md。
> P10 重构于 2026-11-06 启动：双平面证据、LlamaIndex + LanceDB + BGE、受控网络检索、流程/术语内化与 120 题验收；第一阶段 P10-GOV-136 已建立治理基线。M1/M2 已完成，WP6 在 P10 中实现。

- Status: active plan; WP1 is closed with 63 registered sources and no open candidates; WP2 indexes 28 public documents (785 chunks, index `20910f0964df`); WP3 and WP4 are implemented as an extractive prototype with an LLM answer layer; WP5 evaluation runs a reviewed 48-question set (33 dev + 15 test) and a deterministic 38-point coverage harness; WP6 is implemented in the P10 service task. The P10 refactor is tracked in section 3a.
- No versioned releases are published. Milestones describe work stages, not release numbers.
- Architecture: [architecture.md](architecture.md); evaluation: [evaluation.md](evaluation.md); scope: [../PROJECT.md](../PROJECT.md).

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

WP0 is complete. WP1 is closed with 63 registered sources and no candidates: 1 law, 20 regulations, 12 notices, 17 standards, 10 statistical yearbooks (nine fishery yearbook editions for data years 2017–2025 and the China Statistical Yearbook 2026), 2 data dictionaries and 1 operations reference. The 3,126-row core CSV is built locally and has passed source-hash and spot-value checks. Three coverage gaps remain documented: no port infrastructure table for data years 2018–2019, no marine vessel-length table for 2024, and a sampled data year 2025. The 2026-11-01 sufficiency review accepted the draft question set (ten answerable, six partial and eight abstention tests at that time); the instrument now holds 48 questions (33 dev + 15 test), 31 anchor questions and 11 abstention tests. WP2 indexes the 28 public documents into 785 chunks with section and page anchors; the index holds no internal source. Anchor-level Recall@5 is 19/19 with MRR 0.68, abstention 7/8 (one false refusal), citation resolution 1.00 and P95 19 ms; the extractive prototype makes no generative model call. The CWP reference collection answers Q-E05 and Q-M04 (2/2); Q-E08 and Q-M09 remain parked. P06 exposes the yearbook indicator table locally via `scs-fkb stats` (2/2). The register uses source schema v4 (`level`, `authority_tier`, `source_class`, `provenance`, `effective`, `quality`, `currency.cadence`, `license`, `sensitivity`, `lifecycle`, `retrieval`), enforced by `src/scs_fkb/registry.py`; 63 v3 entries are normalised to v4 without changing ids or hashes. A curated watch list runs read-only; changed pages become candidates in `configs/candidates.yaml` and are never ingested automatically. `src/scs_fkb/candidates.py` validates the queue, and `scs-fkb sources check` makes the review date, licence and tier a CI gate. WP3 and WP4 are implemented; WP5 evaluation is in progress on the 48-question set; WP6 is implemented in the P10 service task.

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
| P10-KB-141 | 15 playbooks, 150 terms, 200 facts, extraction/review, weekly loop | Validators green; weekly report reproducible |
| P10-ANS-142 | Answer composer/validator, FastAPI `/v1`, Web UI and feedback | 20 scenarios; citation resolution 100%; localhost service |
| P10-EVAL-143 | 120-question set, RAGAS-compatible metrics, regression gate, docs sync | Acceptance thresholds met; release gate clean |

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

P10-KB-141 is implemented: 15 approved playbooks with 32 fact-cited steps, 150
terms (116 approved, 34 draft), 200 facts (80 approved, 120 draft provision
facts), a playbook validator and a read-only weekly report. The checks are green
and the weekly report records 63 sources, 26 watch entries, 200 facts, 150 terms,
15 playbooks and 6 gaps. The next task is P10-ANS-142.

The architecture decisions are [0005](adr/0005-two-plane-evidence.md),
[0006](adr/0006-llamaindex-lancedb-bge.md),
[0007](adr/0007-controlled-web-evidence.md) and
[0008](adr/0008-playbooks-and-terms.md). The construction standard is
[rag-standard.md](rag-standard.md). Sources, data, indexes and run artifacts stay
outside the public tree; no tag or release is created.

### Source gate and candidate queue (2026-11-04)

- Schema v3 adds `currency.cadence` with a per-cadence cap on `review_due - as_of` (monthly 60 days, quarterly 150, annual 400, semiannual 240, static 550). The 63 sources were migrated by class: normative `monthly`, standard `quarterly`, `official_statistics` `annual`, reference `semiannual`; hashes, dates, locations and statuses are unchanged.
- `license` and `sensitivity` are checked against the allowlist in `configs/schema.yaml`; tier and level must agree (C municipal only, D non-official only, A/B never municipal or non-official).
- `scs-fkb watch --propose` writes proposals to the watch report only. A proposal enters `configs/candidates.yaml` as `open`, is due after 90 days and expires after 180; `accepted` needs a registered `source_id`, `rejected` needs a note, and a duplicate URL is rejected.
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
