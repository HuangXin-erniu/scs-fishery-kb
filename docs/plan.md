# Project Plan

> **中文摘要**：本文件把项目范围拆成 WP0–WP6 工作包、M0–M4 阶段、角色、质量门与风险。
> 里程碑是工作阶段，不是版本；项目不创建 tag 或 GitHub Release。
> 当前处于 WP1（语料采集与登记）：已登记 9 版统计年鉴、6 份全国公报、中国统计年鉴 2026 和 24 份法规与技术文件，候选源已完成处置（3 个暂缓），并生成 3,126 行本地核心指标长表；三处缺口已记录（2025 数据年为抽样）；充分性复核已接受；M1 管线按所有者决定继续推迟。

- Status: active plan; WP1 has nine yearbook editions, six national bulletins, the China Statistical Yearbook 2026, twenty-six legal and technical documents, three candidates and a 3,126-row local core CSV; the sufficiency review is accepted (ten answerable, six partial, eight abstention tests). M1 now runs locally as an extractive prototype over the twenty-nine public sources.
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

WP0 is complete. WP1 is closed for this phase: forty-five sources are registered as nine yearbook editions (data years 2017–2025), six national statistical bulletins (data years 2020–2025), the China Statistical Yearbook 2026, twenty-six legal and technical documents (one law, ten regulations, four notices, six standard sets, one operations reference, one port plan and three reference dictionaries) and three candidates (all deferred). The yearbooks are internal, local-use sources. The 3,126-row core CSV is built locally and has passed source-hash and spot-value checks. Three coverage gaps are documented: no port infrastructure table exists for data years 2018–2019, no marine vessel-length table exists for 2024, and data year 2025 is sampled from the scan rather than fully extracted. The sufficiency review is accepted: ten questions are answerable, six partial and eight abstention tests. The legal corpus spans the national level and Guangdong, Guangxi and Fujian; the Fisheries Law is registered from the official People's Daily publication of 2026-02-25, with the duplicate copies removed, and the npc.gov.cn page itself returned HTTP 403 from this network on 2026-10-31. The 2026 closed-season special-permit notice is registered from the ministry's official OFD attachment, including the two South China Sea permits it creates. WP2 now covers the twenty-nine indexed public sources: they parse into 703 chunks with article, section and page anchors, and the local index holds no internal source. Anchor-level Recall@5 is 8/11 on the eleven questions with gold anchors, the evidence gate abstains on five of six out-of-scope tests with two false refusals, and every returned citation resolves. The prototype is deterministic and makes no model call. A Chinese-to-English term bridge feeds a reference channel that returns the CWP definition passages for Q-E05 and Q-M04 (2/2) without entering the main index. WP3–WP6 remain deferred. M2 is now compared on the same instrument: BM25 8/11, BM25 plus lexicon 9/11, dense-only 8/11 and hybrid 10/11 with MRR 0.45 and P95 17 ms, all at abstention 5/6 and two false refusals; the hybrid configuration is adopted.

## 4. Milestones

| Milestone | Content | Exit condition |
|---|---|---|
| M0 | Framework and public baseline | Scope, architecture, plan, evaluation, corpus register, questions and CI are published |
| M1 | Minimal pipeline | Two or three documents are parsed, indexed and answerable with citations |
| M2 | Retrieval baseline | BM25, dense and hybrid retrieval are compared on a reviewed subset |
| M3 | Evaluation and service prototype | Citation/answer metrics and an end-to-end CLI/HTTP demonstration are reported |
| M4 | Interface contract | The `/v1` contract is reviewed; no data integration is included |

Milestones do not create releases or tags. Completion is judged by the exit condition and the quality gates below. M1 is deferred until the corpus matrix is sufficient; the current phase is WP1.

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
