# Project Log

This log records material project changes by date. It does not use release versions and is not tied to GitHub Releases.

## 2026-11-05 — Atomic fact spot-check

- Reviewed the 20 atomic facts (17 policy, 3 gear) against their cited sections. Values that summarised more than their short quote were either narrowed or given a longer verbatim quote; `FACT-POLICY-003` now carries the special-permit area/port qualifiers, and `FACT-GEAR-002` is limited to class names/codes while `FACT-GEAR-011` carries the name/code writing order.
- `facts check --today 2026-11-05`: 80 facts, 80 approved, 0 errors, 0 conflicts, 0 expired. External store rebuilt to 375 documents / 431 chunks, index `3259a7694499`; corpus remains 28 documents / 785 chunks / `20910f0964df`.
- Per-fact review table: `runs/P09-KB-132/atomic-review.md` (private). No corpus, index, retrieval or answer-path change.


## 2026-11-04 — Verified fact layer, terminology and FAQ

- Added `configs/facts/{policy,gear,stats}.yaml`: 80 approved facts (20 atomic + 60 provision; 64 policy, 13 gear, 3 stats). Every fact carries a verbatim evidence quote, source document/section and register hash; atomic facts add precise values and effective dates.
- Added `configs/terms.yaml` (24 terms from colloquial variants to standard wording) and `configs/faq.yaml` (12 public FAQs across the four personas). FAQ claims resolve to approved facts; no eval, gold or real-user question is used.
- Added `facts.py`, `terms.py` and `faq.py` plus `facts check`, `terms check` and `faq check`. `facts check --data-root` verifies evidence, hashes, effective dates, conflicts and expiry; the 80 facts pass with 0 errors and 0 conflicts.
- Rebuilt the external store with facts/terms/FAQs: **375 documents, 431 chunks, index `f3eb84266cfa`** (119 cards, 140 notes, 80 facts, 24 terms, 12 FAQs). The corpus store is unchanged at 28 documents, 785 chunks and `20910f0964df`; the answer path is unchanged.
- Tests: 333 passed, 2 skipped.


## 2026-11-04 — Four-persona held-out evaluation split

- Added 15 test questions (12 anchors, 3 abstention) across captain/crew, owner/operator, enforcement and extension: Q-C01..Q-C04, Q-O01..Q-O04, Q-F01..Q-F04 and Q-T01..Q-T03. The existing 33 questions stay unchanged as dev.
- Added `meta` to `configs/eval.yaml` (persona/split for all 48 questions) and split/persona reporting in `eval`: `summary_split`, `summary_persona`, `coverage.by_split` and `llm.averages_by_split`.
- Evidence audit: the 12 anchors point at indexed sections (POL-WATCH-082, POL-PEN-078, POL-STD-010, POL-RULE-019, POL-PEN-080, POL-ENF-068, POL-RULE-018, OPS-STD-039, OPS-STD-035); the 3 abstention questions have no supporting source. 22 new gold points each carry a deterministic check.
- Baseline: extractive dev 19/19 anchors, 7/8 abstention, MRR 0.6816, coverage 10/38; test 12/12, 1/3, MRR 0.8542, coverage 2/22. LLM dev 19/19, 8/8, 0.7605/0.6605/0.9421, coverage 15/38; test 12/12, 3/3, 0.7125/0.7083/0.8958, coverage 10/22. Test is report-only and is not used for tuning.
- No change to the corpus, index, retrieval or answer path; no new sources.


## 2026-11-04 — Source currency gate and candidate admission queue

- Source schema moves to v3: `currency.cadence` is required and bounds `review_due - as_of` (monthly 60 days, quarterly 150, semiannual 240, annual/edition 400, weekly 21, daily 3, irregular 180, static 550). The 63 registered sources were migrated by class — normative monthly, standard quarterly, official_statistics annual, reference semiannual — with hashes, dates, locations and statuses unchanged.
- `license` and `sensitivity` are now checked against the allowlist in `configs/schema.yaml`; tier and level must agree (C municipal only, A/B never municipal). `cc-by-nc-sa-3.0-igo` is an accepted public licence.
- Added `configs/candidates.yaml` and `src/scs_fkb/candidates.py`: a candidate is a proposal with `open`/`accepted`/`rejected`/`expired` status, a 90-day due mark, a 180-day expiry, a required `source_id` on acceptance, a required note on rejection and duplicate-URL rejection. Nothing is ingested automatically.
- `scs-fkb watch --propose` emits proposals to the watch report and leaves both config files byte-identical. `scs-fkb sources check --today YYYY-MM-DD [--grace-days 30]` fails on overdue sources, malformed/expired candidates or an accepted candidate whose source is missing; it runs in `make check` and CI.
- Verification: 104 focused tests pass; `sources check --today 2026-11-04` reports 63 sources, 0 overdue; `--today 2027-01-15` reports 33 overdue and exits 1. No corpus, index, card or note change.

## 2026-11-04 — Deterministic gold-point coverage baseline

- Added eval-only `checks` for all 38 gold points across the 19 anchors and a `coverage` block in `eval`/`eval --llm`; every point is checked against cited answer sentences and missing terms are reported.
- Baseline: extractive 10/38 (0.26), LLM 15/38 (0.39). The gap is secondary items already present in the index, not missing sources.
- Clause-level indexing was measured and deferred: hybrid top-5 recall fell to 16/19 and abstention to 6/8; the baseline index `20910f0964df` was restored.
- Next: use the missing-point list to drive slot retrieval and claim gating (P08-RAG-129).

## 2026-11-04 — Completeness pass: human review override added, prompt variants rejected

- Added `--review` and `--review-template` to `scs-fkb eval --llm`: the reviewer can override correctness/completeness/faithfulness per question, and the report marks those rows as human.
- Tested three completeness levers: a multi-part prompt (v4), a stricter item-by-item prompt (v5), and top-document evidence expansion. Completeness fell from 0.66 to 0.61, 0.56 and 0.37, so all three were rejected and the v3 baseline was restored.
- Root cause is evidence coverage: several gold points (for example Q-E02's four special-permit gear types, Q-M01's legal basis, Q-M15's sampling strata) are not in the retrieved context. The next step is evidence-level retrieval, not more prompt wording.
- Human review template: `runs/P08-RAG-123/review-template.yaml`; no corpus or index change.

## 2026-11-04 — LLM answer layer fixes Q-E07 and Q-E12

- Added a public-only LLM client for the OpenCode Go OpenAI-compatible endpoint (`deepseek-v4.1-flash`, low reasoning effort) with an explicit `--llm` flag, TLS verification, retries and a stable `x-opencode-session`.
- Added an evidence judge and answer generator: Q-E07 now abstains because the evidence only lists other fishing grounds; Q-E12 answers from `POL-LAW-009` §第七十八条 with a valid citation.
- The deterministic extractive path remains the default and the fallback when the LLM is unconfigured, errors, or returns an invalid citation.
- Model-assisted scoring against the reviewed gold points: correctness 0.76, completeness 0.66, faithfulness 0.94; hybrid 19/19 anchors, 8/8 abstention, 0 false refusals. These are model-assisted, not human review.
- No corpus, card, note or index change; the key stays in the untracked `.env`.

## 2026-11-04 — Evaluation v1 reviewed; per-question answer metrics added

- The project owner reviewed the question set in three batches; the set now has 33 questions: 19 anchors, 8 abstention tests, 2 CWP reference questions, 2 statistics questions and 2 deferred web questions.
- Added gold answer points and evidence anchors to `configs/eval.yaml`; rewrote Q-E03, Q-E06, Q-E09, Q-E10, Q-E12 and Q-M03, and moved M02/M06/M11 to abstention tests where no dictionary exists.
- The eval report now carries per-question answer text, citations, refusal reason and deterministic citation-coverage/faithfulness scores. Hybrid baseline: 19/19 anchors, MRR 0.68, abstention 7/8, one false refusal, answer rate 18/19, citation resolution 1.00, citation coverage 0.99, faithfulness 1.00, P95 20 ms.
- RAGAS is deferred until an LLM API key is configured; human correctness and completeness are not yet scored.
- No corpus, card, note or index change.

## 2026-11-03 — Hybrid retrieve fixed; public docs aligned to the adopted baseline

- Fixed `scs-fkb retrieve` under the adopted hybrid mode: `_retrieve` now passes the data root to the retriever, matching `ask`; added a CLI regression test.
- Synced the current-state sections of README, PROJECT, evaluation, plan, knowledge, corpus, questions, data-policy and index to the measured baseline: 63 sources and 0 candidates; 28 documents, 785 chunks, index 20910f0964df; hybrid 11/11, MRR 0.56, abstention 3/4, citation resolution 1.00; external store 259 documents and 315 chunks.
- Historical bullets and project-log entries keep their original figures; only current-state statements were corrected.
- No corpus, config, index or data change; the corpus baseline stays 20910f0964df.

## 2026-11-03 — Product-manual probe and operating rhythm

- OLCI Marine User Handbook PDF is reachable and parses to 88,763 characters; the PO.DAAC MUR page fails at TLS. Neither is carded yet because Q-E08 and Q-M09 need both.
- Documented the rhythm: weekly watch, monthly refresh, quarterly review 2027-02-02; due items are prompts, never automatic rewrites.
- Added glossary terms source_class, currency, review_due and web card.
- Adopted baseline unchanged: 36 documents, 849 chunks, index 5135e00cfa3d, hybrid 11/11.
## 2026-11-03 — Online watch: 22 ok, 4 changed queued

- Ran the first online watch after the card layer: 22 entries ok, 4 changed (WATCH-GD-NOTICES, WATCH-GX-NYNCT-NOTICES, WATCH-GX-HYJ-NOTICES, WATCH-MOJ-OBSERVATION).
- Changed is a review prompt, not an update; the four pages are queued, baselines unchanged, no corpus entry modified.
- Quarterly review reminder set for 2027-02-02; gap file has one entry.

## 2026-11-03 — Placeholder URLs cleaned, gap report added, review rehearsed

- Removed the three example.invalid URLs from policy notes; document sources now carry no URL rather than a fake one.
- Added `scs-fkb knowledge gaps`, grouping gaps.jsonl by nature, domain and reason; current file has one definition/general/weak_evidence entry.
- Rehearsed the quarterly procedure (knowledge check, watch --offline): 0 stale, 0 due, 26 watch entries ok. The real sweep remains 2027-02-02.
- No corpus or index change; baseline stays 20910f0964df.

## 2026-11-03 — Cards join the external index; refusals become gaps

- Linked the card cache into the external root and rebuilt it: 259 documents / 315 chunks (119 cards + 140 notes), external index `0c6d3901106c`, dense `0d3640622f4fbf90`.
- Added record_gap and wired it into ask: every refusal appends timestamp, question, reason, nature and domain to `$SCS_FKB_DATA_ROOT/gaps.jsonl`; write failures never affect the answer.
- Verified: a corpus question still answers with labelled external support; an out-of-scope question abstains and records the gap.
- Corpus baseline unchanged: 20910f0964df, hybrid 11/11, abstention 3/4.

## 2026-11-03 — Two-index architecture: corpus decides, external supplements

- Ingest gained --external-only: it skips corpus documents and writes cards/notes to a separate data root. The external store holds 140 notes (the card cache lives beside the corpus root).
- Ask now queries the external index only after a non-abstained corpus answer and appends labelled supporting evidence; abstention is untouched.
- Built and embedded the external store (140 documents, 140 chunks); corpus baseline stays 20910f0964df with hybrid 11/11 and abstention 3/4.
- Fixed ask to tolerate the removed product collection and hid placeholder URLs in external citations.

## 2026-11-03 — Claim matrix applied as evidence filter

- Chunks now carry source_class, trust and review_due; web cards are standard/reference, notes inherit trust from their sources, corpus chunks from the register.
- claims.select_evidence filters hits by nature, trust, kind and freshness; no admissible primary means abstain.
- Measured the 287-document index: BM25 abstention 3/4 but hybrid 9/11 with abstention 2/4; the enlarged dense pool itself changes corpus ranking, so the filter alone cannot restore the baseline.
- Restored the corpus-only index (28 documents, 785 chunks, 20910f0964df): hybrid 11/11, abstention 3/4. Notes and cards stay unindexed.

## 2026-11-03 — Two-level claim taxonomy and router

- Added configs/claims.yaml: seven claim natures with freshness windows and primary-evidence rules, seven domains with keyword lists.
- Added src/scs_fkb/claims.py: deterministic classifier with a general fallback; tests cover every nature, domains and unknown input.
- Documented the taxonomy, trust tiers, primary/supporting/conflict rules and four internalisation triggers in docs/knowledge-policy.md.
- No index change; the corpus-only baseline stays in force until the router is wired into answering.

## 2026-11-03 — Layered corpus gate implemented, enlarged index still deferred

- Added a chunk kind (corpus/web/note) and a corpus-evidence gate: cards and notes cannot alone support an answer; `answer.require_corpus_evidence` switches it.
- Measured the 287-document index: BM25 abstention recovered to 3/4, but hybrid stayed at 2/4 with recall 9/11. The gate does not yet make the enlarged index safe.
- Restored the corpus-only index (28 documents, 785 chunks, 20910f0964df): hybrid 11/11, abstention 3/4.
- Gate code and tests remain for the next design attempt; cards and notes stay unindexed.

## 2026-11-03 — Knowledge notes wired into ingest, indexing deferred

- Ingest now builds NOTE-* documents from approved notes and skips drafts, stale notes and expired hazard notes; `--no-web` and `--no-knowledge` allow controlled rebuilds.
- Measured 287 documents with cards and notes: hybrid 9/11, abstention 2/4. Measured 147 documents with cards only: hybrid 11/11, abstention 2/4. Both fail the abstention gate, so neither is adopted.
- Restored the corpus-only index: 28 documents, 785 chunks, `20910f0964df`, hybrid 11/11, MRR 0.56, abstention 3/4.
- The knowledge layer stays complete and validated; indexing awaits an abstention-aware gate for external evidence.

## 2026-11-03 — Remaining knowledge domains filled

- Added nineteen notes: policy 7 (crew, ports, penalties, Hainan and Guangxi 2026 closures, distant-water monitoring, e-certificates), gear 5 (mesh standards, GB/T 5147—2026, SC/T 9460—2025, closure operation types), stats 3, hazard 3 and environment 1.
- Knowledge base now holds 140 notes across six topics, every one with a SHA-256-pinned source and a review date.
- 0 stale, 0 due; no index change, adopted baseline stays 36 documents / 849 chunks.

## 2026-11-03 — Species knowledge scaled to 115 notes

- Added configs/species-seed.yaml (116 species) and src/scs_fkb/knowledge_build.py; each seed becomes a WoRMS card and a note built from the returned record.
- Fetched 115 of 116 cards; Prionace glauca failed with a TLS reset and produced no note. Species notes now total 115 (4 pilot + 111).
- Facts cover scientific name, authority, classification, marine flags and AphiaID; distribution and protection status remain explicitly unverified.
- No index change; adopted baseline stays 36 documents / 849 chunks.

## 2026-11-03 — Knowledge-note layer with a ten-note pilot

- Added configs/knowledge/<topic>.yaml and src/scs_fkb/knowledge.py: schema validation, card-hash binding, hazard expiry, due reporting and draft-to-approved flow.
- Added `scs-fkb knowledge list/check/approve`; check --write marks changed or expired notes stale and never approves them.
- Seeded ten notes: four WoRMS species, three policy notes from POL-CLOS-015, POL-STD-010 article 28 and POL-SPEC-041, one FAO gear note, one EUMETSAT environment note and one warning-signal hazard note.
- No index change; the adopted baseline stays 36 documents / 849 chunks / 5135e00cfa3d.

## 2026-11-03 — Q-M10 reworded, Q-E01 synonym added, card baseline adopted

- Q-M10 now asks 申请海洋渔业捕捞许可证应当提交哪些资料？; anchors are unchanged (POL-STD-010 第二十八条, POL-LAW-009 第三十五条).
- One active lexicon group 起止日期 → 休渔时间 recovered Q-E01.
- Full eval on the 36-document index: hybrid 11/11, MRR 0.56, abstention 3/4, two false refusals, citation 1.00; BM25 8/11, lexicon 10/11, dense 8/11; reference 2/2, statistics 2/2, jurisdiction 3/3, national 2/2.
- The 36-document card baseline is adopted; the 28-document row stays as history.

## 2026-11-03 — Watch report lists review dates

- Added due_report to watch.py: corpus entries whose currency.review_due has arrived and ok cards whose fetched_at plus topic cadence has arrived.
- The watch handler adds the lists to the JSON report and prints one line per due item; nothing is refreshed automatically.
- Tests cover due/not-due corpus dates, card cadence and exclusion of failed cards.

## 2026-11-03 — Environment and hazard cards added

- Allowlisted nasa.gov and eumetsat.int, and fetched three static pages: the 2007 warning-signal measures (gov.cn), the NASA Ocean Biology DAAC ocean-colour page and the EUMETSAT Sentinel-3 page.
- Eight cards are now ok; the FAO card was retried after a transient TLS EOF. Copernicus PUM PDF (TLS reset) and PO.DAAC MUR (timeout) failed and are recorded.
- Rebuilt at 36 documents / 849 chunks (index 5135e00cfa3d, dense 56b9551d4b080bc3); arms unchanged, so the measurement stays interim and the 28-document baseline stays adopted.

## 2026-11-03 — Retrieval tuning reviewed, baseline kept

- Measured title_boost 0/0.5/1/2, BM25:dense 2:1/1:1/1:2 and three lexicon expansions; none recovered Q-M10, and lexicon changes cost two other questions.
- Kept title_boost 1.0 and BM25:dense 2:1, the 28-document baseline adopted, and the 33-document card measurement interim.
- Added a test pinning the reviewed parameters so future changes are deliberate.

## 2026-11-03 — Five cards seeded and the index rebaselined

- Extended the refresh extractor to accept JSON and plain text, and added certifi-backed TLS context with a file fallback (never an unverified context).
- Fetched and cached five allowlisted cards: four WoRMS Aphia records (大黄鱼, 带鱼, 蓝圆鲹, 中国明对虾) and the FAO ISSCFG gear-classification page; fetched 2026-11-03, hashes 0949f07c…, d32d0821…, 52d13dc4…, bd073fad…, 516e1eeb….
- Rebuilt the index at 33 documents and 795 chunks (index 4c5264cc338c, dense c00adfa568d06e10); every arm is unchanged. Because hybrid remains 9/11, the 33-document measurement is recorded as interim and not adopted; the corpus-only 28-document row stays the baseline.
- Q-E08 and Q-M09 stay parked: the MUR/OLCI product pages are JavaScript applications.

## 2026-11-03 — Web cards indexed beside the corpus with URL citations

- Chunk and Citation now carry url and retrieved_at with defaults, so old records still load.
- Ingest turns each ok, cached card into a document (doc_type web_card) and chunks its text, attaching the card URL and fetch date; failed or cache-less cards are skipped.
- Citations render as `[WEB-xxx] https://… (fetched date)`; the manifest records web cards with parser web and kind web_card.
- With configs/web-cards.yaml empty, the index is unchanged at 28 documents / 785 chunks / 20910f0964df.

## 2026-11-03 — Web card layer with an allowlisted refresh command

- Added configs/web-sources.yaml (17 allowlisted domains, four topics, 30-day cadence, TLS/rate/size limits) and configs/web-cards.yaml (public card metadata, empty until the first refresh).
- Added `scs-fkb web refresh` and `scs-fkb web check`: https-only, exact-host or subdomain matching, verified TLS, 4 MB cap, per-card failure isolation; text goes to the private data root, metadata stays public.
- Added tests/test_web.py with a fake fetcher; the suite stays offline.
- Index unchanged at 28 documents / 785 chunks / 20910f0964df.

## 2026-11-03 — Product documents and ASFIS removed, CWP kept

- Deleted STD-MUR-045, STD-OLCI-046, DICT-GFW-048, STD-CMEMS-049, STD-HY1-056 and STD-ASFIS-044, with their data files and the product reference collection.
- Kept STD-CWP-043 as the definitions core: Q-E05 and Q-M04 still hit, so the reference set is 2/2; Q-E08 and Q-M09 moved to a `web` queue and will be restored with cached cards in phase three.
- Register: 63 sources, 63 acquired; fishery_product 0, data_dictionary 2; counts elsewhere unchanged; main index still 28 documents / 785 chunks / `20910f0964df`.

## 2026-11-03 — Validity model replaced by source class and currency

- Removed `validity` from all 69 entries: the in-force / not-applicable / unknown states are gone, and category notes were dropped because the class now states what the source is.
- Added `source_class` (33 normative, 10 official_statistics, 18 standard, 8 reference) and `currency` (as_of 2026-11-03; review_due 2026-12-03 for normative, 2027-02-01 for standard, 2027-11-03 for official statistics, 2027-05-02 for reference). Evidence sentences moved into `currency.note`.
- The validator now rejects a legacy validity block, a bad class, a bad basis, a malformed date and a review date before the check date.
- Index unchanged at 28 documents, 785 chunks, index 20910f0964df.

## 2026-11-03 — Nine dead entries removed and the index rebuilt

- Deleted the three unacquired candidates, the retired SC/T series, the 2017 and 2020 monitoring circulars, the permit-form instruction, the expired 2018-2025 port plan and the port-list proposal, with their data files; the proposal was the last unknown.
- Register: 69 sources, 69 acquired, no candidates, no retired entry, no unknown (51 in_force, 18 not_applicable); policy collection 30; pipeline 28 documents.
- Rebuilt at 28 documents and 785 chunks (index 20910f0964df, dense 58ded7342e4c66fe). Hybrid 9/11 (MRR 0.42) after losing Q-M10 to the smaller index; published as measured, with a retrieval follow-up noted. Reference 4/4, statistics 2/2, jurisdiction 3/3, national 2/2 unchanged.

## 2026-11-03 — Vessel-monitoring measure closed

- `POL-VMS-053` moved to in_force: 农渔发〔2019〕22号 (2019-08-01), Article 32 states 本办法自2020年1月1日起执行, and the 2014 predecessor is repealed. The earlier sweep missed the clause because it searched for 施行 rather than 执行.
- Unknown set is now exactly `POL-PORT-037`; status counts 51 in_force, 26 not_applicable, 1 unknown. Counts and eval unchanged.

## 2026-11-03 — Twenty-one unknown entries resolved by category

- Four normative documents upgraded with quoted evidence: POL-STAT-050 (本规定自发布之日起施行), POL-STAT-051 (国统制〔2024〕120号), STD-ECERT-054 (three certificate standards published 2025-01-01, now registered from the notice page with the PDFs noted) and POL-GD-061 (published 2026-04-28, 2026 season).
- Fifteen non-normative entries moved to not_applicable with a category-first note: six international product documents, three unacquired candidates, the retired SC/T series, the 2017 and 2020 work notices, the 2018-2025 port plan, the HY-1C/D product note and the permit-form instruction.
- Two remain unknown on purpose: POL-PORT-037 (proposal, no final announcement) and POL-VMS-053 (no commencement clause in the registered text).
- Status counts: 50 in_force, 26 not_applicable, 2 unknown; register 78/75/3 and the eval baseline unchanged.

## 2026-11-02 — Fishery-economy bulletins removed; capture-only statistics

- Deleted STAT-BULL-025 and STAT-BULL-028 to STAT-BULL-032 from the register, the pipeline and the data root: they report total output including culture, and the owner asked for statistics that carry a capture series only.
- Kept the nine fishery yearbooks, the China Statistical Yearbook 2026 and the two indicator definitions; the statistics section still scores 2/2.
- Rebuilt at 31 documents and 846 chunks (index 2ad41cc64de3, dense dd318a16c295a32f). Hybrid holds 10/11 with MRR 0.44; abstention 3/4 with three false refusals (one more than before), published as measured because this is a scope decision.
- Register: 78 sources, 75 acquired; statistical_yearbook 10.

## 2026-11-02 — Full scope audit and boundary guard

- Scanned every active entry's title and notes for aquaculture, breeding, ranching, processing, freshwater and inland terms; no further pure out-of-scope entry remains.
- Recorded the borderline keeps with reasons in docs/corpus.md 5t: the resource levy and stocking regulation (capture instruments), the six fishery-economy bulletins and two indicator definitions (statistical context), the statistical yearbook chapter, the protected-species list and the ASFIS code list.
- Added a test that fails when a new active entry carries an out-of-scope term in its title unless explicitly allowlisted.
- No source deleted; counts 84/81/3 and the evaluation baseline unchanged.

## 2026-11-02 — Out-of-scope breeding and ranch material removed, index rebuilt

- Deleted `POL-BREED-084` (人工繁育国家重点保护水生野生动物名录, aquaculture) and `POL-RANCH-083` (国家级海洋牧场示范区名单, ranching infrastructure) from the register, collection, watch and pipeline, and removed their local files; hashes 6b187aca… and 663f09b4… recorded for audit.
- Removed the four cues created only for them and replaced the two sections with a scope boundary: capture, vessel operations and fishery-condition material in; aquaculture, breeding, ranching production and processing out; the stocking regulation stays because it restores capture stocks.
- Rebuilt the index at thirty-seven documents and 894 chunks (`a28bbbf43a22`, dense `273e42c147570649`): every evaluation arm is unchanged from the thirty-eight-document baseline.
- Register: 84 sources, 81 acquired; notice 15; policy collection thirty-two documents.

## 2026-11-02 — First text-bearing species list

- Registered `POL-BREED-084`, the third-batch list of aquatic wildlife approved for artificial breeding (公告第490号, announced 2021-11-16): ten species with Chinese and Latin names, 318 parsed characters from the attachment doc.
- Added cues 繁育, 水生野生动物 and the document to the policy collection (thirty-four documents); the gazette page is watched for a fourth batch.
- Register: 86 sources, 83 acquired; notice 17. Eval unchanged.

## 2026-11-02 — Provincial validity closed with evidence

- All eleven provincial entries moved from unknown to in_force with the sentence that supports each: the Hainan regulation's 自2014年1月1日起施行 clause, the Fujian notice page's 有效性: 有效 marker, the 2026 Hainan and Guangxi implementations, the three Fujian catalog attachments, and the Guangdong and Hainan catalogs as the latest batches found.
- Provincial unknown count is zero; register validity is now 47 in_force, 21 unknown (national and international) and 17 not_applicable.
- Counts and the evaluation baseline unchanged.

## 2026-11-02 — Channel metadata aligned with the pipeline

- Set retrieval.channel to main for the five documents admitted in the previous batch, so the register no longer contradicts the thirty-eight-document pipeline.
- Added a test that every pipeline document reports channel main; the two can no longer drift apart.
- Register counts and the evaluation baseline are unchanged.

## 2026-11-02 — Five national texts admitted; new baseline at 38 documents

- Added POL-PEN-078, POL-PEN-080, POL-LIST-079, POL-WATCH-082 and POL-RANCH-083 to the main index: 38 documents, 896 chunks, index 499b420f49b0, dense af4b31ca3f941169.
- Removed the script-shell html beside the ranch docx so the single-file directory rule holds; the registered artifact remains the publisher attachment.
- New baseline: hybrid 10/11, MRR 0.44, abstention 3/4, two false refusals, citation 1.00; BM25 6/11, BM25 plus lexicon 7/11, dense 7/11 (MRR 0.30, three false refusals). The dilution is published as measured; the previous row is kept in docs/evaluation.md.
- Register counts stay 85/82/3.

## 2026-11-02 — Navigation watchkeeping and marine ranches

- Registered `POL-WATCH-082` (渔业船舶航行值班准则（试行）, 农渔发〔1999〕10号, listed in force by announcement No. 950; 3,492 parsed characters) and `POL-RANCH-083` (农业农村部公告第644号, eighth-batch marine-ranch list, 978 characters from the attachment).
- Added cues 值班, 航行, 安全, 海洋牧场, 示范区 and both documents to the policy collection (thirty-three documents); the eighth-batch list notes that later batches are not covered.
- Added WATCH-MOA-WATCH-1999 and WATCH-NFTEC-RANCH-644 with live baselines.
- Register: 85 sources, 82 acquired; operations 2, notice 16. Eval unchanged.

## 2026-11-02 — Climate and hazard: documented unavailability

- Checked four official routes for climate and hazard text and recorded each failure in docs/corpus.md 5r: the gov.cn warning-signal text is the 2007 order and the current 2023 revision (气发〔2023〕34号) is not published as text; the cyclone-grade PDF is image-only; the storm-surge and wave standards have no public text; the 2026 emergency plan renders by script.
- Added and baselined WATCH-CMA-RULES and WATCH-MNR-EMERGENCY so a future text upload is detected; no source was registered and no status was invented.
- Register counts stay 83/80/3; every eval arm unchanged.

## 2026-11-02 — Watch baselines and coverage enforcement

- Baselined the ten watch entries that had never run; the list is now fully baselined (23 ok) with the two dynamic pages marked `dynamic: true` because their content churns between requests.
- Added `watch_ref` to seven sources whose page is watched and `watch_note` to sixty-five others, with the reason limited to three categories: internal data edition, international product documentation, or static text rechecked at the quarterly review.
- Added `validate_watch_coverage` to the registry: an active acquired national or provincial source without a valid reference or a note fails the test suite.
- Register counts and every eval arm are unchanged.

## 2026-11-02 — Corpus cleanup: duplicate port list, channel metadata, not_applicable

- Deleted `POL-PORT-078`, which was byte-identical to `POL-PORT-037` (sha256 fe142d1a…) but titled as the final 2025 port list; the original keeps its proposed-recognition note and now records the mistaken duplicate.
- Corrected the retrieval channel of the four national texts admitted to the main index: `POL-ENF-068`, `POL-OBS-072`, `POL-RES-075` and `POL-PORT-077` now report `main`, matching the thirty-three-document pipeline.
- Added the `not_applicable` validity status and migrated seventeen data publications (yearbooks, bulletins, the statistical yearbook and one dictionary); national `unknown` falls from thirty-one to fourteen.
- Fixed the stale counts in plan and README: 83/80/3, twenty regulations, fifteen notices, eighteen standard sets, fifty-six legal and technical documents plus seven reference dictionaries.
- Register: 83 sources, 80 acquired; policy collection thirty-one documents. Eval unchanged.

## 2026-11-02 — General penalty rules and the national validity sweep

- Registered `POL-PEN-080` (渔业行政处罚规定, 农业部令第36号, revised 2022-01-07 and 2025-07-15 by 农业农村部令2025年第3号; 2,780 parsed characters).
- Added the announcement No. 950 cross-check to `POL-RES-075` and `POL-PEN-078`; no status was upgraded without a citation.
- Published a national validity sweep in docs/corpus.md 5q: thirty-one national entries remain unknown, grouped as data publications (17), notices/plans not covered by the catalogue (10), unacquired candidates (3) and the retired series (1), each with the reason.
- Register: 84 sources, 81 acquired; regulation 20; policy collection thirty-two documents; both new rows in the currency table. Eval unchanged at the current baseline.

## 2026-11-02 — Enforcement rules and the in-force catalogue

- Registered `POL-PEN-078` (中华人民共和国渔业港航监督行政处罚规定, 农业部令第34号, revised 2025-07-15 by 农业农村部令2025年第3号; 4,131 parsed characters) and `POL-LIST-079` (农业农村部公告第950号, 2025-09-24 catalogue of rules in force; 11,657 characters).
- The catalogue is used as evidence, not inference: `POL-CREW-055` moves from unknown to in force with the announcement quoted, and `POL-STD-010` carries the same cross-check. The catalogue does not list the fishing-vessel inspection rules (they sit with the transport ministry), so that regulation is not registered.
- Added enforcement cues (处罚, 罚款, 违法, 目录) and both documents to the policy collection (thirty-one documents); added both rows to the national currency table.
- Register: 83 sources, 80 acquired; regulation 19, notice 16. Eval unchanged at the current baseline.

## 2026-11-02 — Watch cover for the new national pages and a currency table

- Added six watch entries with live baselines: the administrative regulations page for the observation regulation, the gov.cn pages for the stocking and port regulations, the marine disaster reduction bulletin list, the forestry announcement page for the species list and the fishery administration port-list attachment.
- Added a national currency table to docs/sources.md: twelve entries with status, as-of date and the event that triggers a review, plus the next quarterly review date (2027-02-02). A changed watch status is a prompt to review, not an automatic update.
- Register counts stay 81/78/3; the eval baseline stays at 33 documents, 794 chunks, index cd97744aa292, hybrid 10/11.

## 2026-11-02 — Four national texts admitted; new baseline published

- resolve_source_file now accepts a single-file directory, so sources that carry their document in a directory can enter the pipeline; empty or multi-file directories are rejected with tests.
- Added POL-ENF-068, POL-OBS-072, POL-RES-075 and POL-PORT-077 to the main index: 33 documents, 794 chunks, index cd97744aa292, dense f15c73a5996702f5.
- New baseline: hybrid 10/11, MRR 0.45, abstention 3/4, two false refusals, citation 1.00; BM25 7/11, BM25 plus lexicon 8/11, dense 8/11 (MRR 0.32, three false refusals). The comparison-arm drop is the expected dilution from 121 new chunks and is published rather than smoothed; the adopted hybrid arm is unchanged, so the batch is kept.
- Registered-source counts stay 81/78/3.

## 2026-11-02 — Port and operations layer opened

- Registered `POL-PORT-077` (中华人民共和国渔港水域交通安全管理条例, 国务院令第38号, amended 2019-03-02; 2,548 parsed characters) and `POL-PORT-078` (2025年第一批渔港等级认定名单, ministry attachment docx, 266 characters, twelve central ports and the first-class ports).
- Added port cues (渔港, 锚地, 避风, 泊位, 靠泊) and both documents to the policy collection (twenty-nine documents).
- Shelter anchorages recorded as unattainable: no national public list, only foreign regulations and provincial references. The 12 operation types stay covered by POL-STD-010 and the gear standards.
- Register: 81 sources, 78 acquired; regulation 18, notice 15. Eval unchanged on every arm; the port probe returns POL-PORT-077 three times.

## 2026-11-02 — Species and resource-conservation layer opened

- Registered `POL-RES-075` (水生生物增殖放流管理规定, 农业部令第20号, in force, 1,676 parsed characters) and `STD-SPEC-076` (国家重点保护野生动物名录, 2021年第3号, image-only PDF registered as provenance with parseable false).
- Added species cues (物种, 保护, 名录, 放流, 增殖, 种质); the stocking regulation joined the policy collection while the image-only list stays provenance with channel none, so no collection document is unparseable.
- Recorded two limits: ASFIS is a zip lookup the parser cannot read, and the germplasm-reserve download returned the superseded 2013 eco-environment bulletin.
- Register: 79 sources, 76 acquired; regulation 17, notice 14. Eval unchanged on every arm.

## 2026-11-02 — Environment and marine-hazard layer opened

- Registered `POL-OBS-072` (海洋观测预报管理条例, 国务院令第615号, revised 2023-07-20; 5,208 parsed characters), `STAT-ECO-073` (2025 中国海洋生态预警监测公报, 76 pages, 80,304 characters, published 2026-06-08) and `STAT-DIS-074` (2023 中国海洋灾害公报, 52 pages; text layer garbled, so provenance only with parseable false).
- Added environment cues (观测, 预报, 海洋灾害, 赤潮, 绿潮, 海温, 生态, 灾害) and the three documents to the policy collection (twenty-seven documents).
- Rejected the 2026 marine disaster emergency plan (body rendered by script on both ministry and gov.cn pages), the image-only GB/T 19201-2006 cyclone-grades PDF and the script-shell forecast-centre site; typhoon grading stays uncovered.
- Register: 77 sources, 74 acquired; regulation 16, notice 13. Eval unchanged on every arm; the ecological-bulletin probe returns STAT-ECO-073 three times.

## 2026-11-02 — Guangxi hull catalog: not public, disclosure request prepared

- The provincial notice and document lists answer 200 but are script shells; the former ocean-bureau domain and the Qinzhou approval that cited the catalog both return 404; the only reachable text is an inland pontoon standard, which is out of scope. The catalog cannot be registered from public pages today.
- Added docs/foi-guangxi-hull-catalog.md: a ready-to-submit government-information disclosure request with the exact scope (hull name, main dimensions, power, tonnage, material, gear, area, publication number, date, validity), the legal basis, the channels, the materials and the 20-working-day clock. Submission is the owner's action; the project records the outcome.
- Added the provincial notice list and the ocean-bureau notice list to the watch with recorded baselines; the provincial https endpoint presents a hostname-mismatched certificate, so the monitor uses http and records the limitation.
- No source registered; 74/71/3 unchanged and every eval arm unchanged.

## 2026-11-02 — 2018 national evaluation results recorded as unattainable

- Searched four phrasings, the ministry and bureau search endpoints (both HTTP 404), gazette issues 201804–201812 (script shells, zero 标准船型 occurrences) and archive.org (timeout). Only news restatements exist, so the 66-type list is recorded as unattainable and not reconstructed.
- `STD-YY-071` now names 农业农村部公报 2018 年第 11 期 as the predecessor of the 2021 and 2024 editions, without registering the superseded text.
- Added the bureau notice list to the watch with a recorded baseline, so a future hull-type evaluation announcement is detected.
- No source registered; 74/71/3 unchanged and every eval arm unchanged.

## 2026-11-02 — Cleanup: one hard delete, one retirement, level corrections

- Hard-deleted `DICT-GFW-047` under decision D-SCS-FKB-058: licence unknown with no official provenance, so it left the register, the product collection and the data root. Its file hash `5a5e83ec804a3969d7ee93f28b15e08002363659e460d3c0827ff537779704b4` is recorded here for audit.
- Retired `STD-SC-042` (17 SC/T standards, image-only, no text layer): lifecycle retired with date, reason and decision key, retrieval stays `none`, and the hash and local file are kept as provenance rather than deleted.
- Corrected four levels from national to international for the remote-stack sources whose jurisdiction is international: `STD-MUR-045`, `STD-OLCI-046`, `DICT-GFW-048`, `STD-CMEMS-049`, all tier B.
- `STD-ASFIS-044` stays active for the species task; `STAT-YB-2026` stays active because its data reaches the project through the statistical extracts.
- Register: 74 sources, 71 acquired, 3 candidates; product collection five documents; every eval arm unchanged.

## 2026-11-02 — Registry schema v2 and migration

- Added `src/scs_fkb/registry.py`: loads the register and validates level, authority tier, validity, retrieval and lifecycle, with a retirement block required for retired entries and unique ids enforced.
- Migrated all 75 entries: 61 national, 11 provincial, 2 international and 1 municipal; 29 main-index, 31 collection, 10 statistics and 5 unrouted; 24 entries carry `in_force` with a quoted evidence sentence and 51 carry `unknown` rather than an assumed status.
- Added docs/data-model.md with the field table, enums and the admission, supersession, retirement, deletion and main-index rules; the data policy now states retirement-versus-deletion explicitly.
- Counts and every eval arm are unchanged; the main index is untouched.

## 2026-11-02 — Level-aware ordering and a national evaluation section

- Every policy collection document now carries a level (national, provincial or municipal). The policy lookup sorts stably: named province first, then the national layer, then other provinces and the municipal layer; with no province named, national before provincial before municipal.
- The closure cues 休渔, 伏季 and 执法 are back. The intended consequence is that the national closure question now has a policy block leading with the 2026 enforcement notice instead of an empty block; the province questions still lead with their own documents.
- Added a separately scored national section: J4 expects `POL-ENF-068` and J5 expects `STD-YY-071`, both 2/2. Every existing arm is unchanged.
- Four national pages were added to the watch list with hashes recorded from a live run, so a future change reports as changed rather than unbaselined.

## 2026-11-02 — National hull package completed

- Added `STD-HULL-069` (农办渔〔2017〕5号 notice, 2017-02-07), `STD-HULL-070` (annex 2 usage notes, 4,531 characters) and `STD-YY-071` (远洋渔船标准化船型参数系列表 2024年版, 农办渔〔2024〕15号, 10 pages, effective 2024-12-01). The 2017 method now has its promulgating notice and its explanatory annex, and the national layer has one parameter table.
- Validity blocks added to the four national hull entries. The 2024 series names the 2021 edition as the superseded predecessor but does not register it. A scope note on `STD-YY-071` says the hull types are ocean-going and must not answer near-shore parameter questions; the provincial catalogs stay the near-shore reference.
- The 2018 quarterly evaluation results (66 types, including Guangxi) stay unattainable: only news restatements were found, no publisher page. SC/T 8003-2007 is recorded as the code standard with no dimensions, so it cannot substitute for a parameter catalog.
- Register: 75 sources, 72 acquired; standard 18. The cue list is unchanged, so the closure question still answers from POL-CLOS-015 §三 with an empty policy block. Eval unchanged on every arm.

## 2026-11-02 — National closure enforcement notice and validity blocks

- Added `POL-ENF-068`, the 2026 joint enforcement notice of 农业农村部, 公安部 and 中国海警局 (2026-04-29, 4,767 characters): 1 May to 16 September, three priority tasks. It is an enforcement deployment under 农业农村部通告〔2023〕1号, not a change to the closure system.
- Added a validity block (status, as_of, note) to POL-LAW-009, POL-STD-010, POL-CLOS-015, POL-RULE-018, POL-SPEC-041 and the new notice, so in-force status is recorded with its evidence: the 2023 notice is cited by the 2026 Hainan and Guangxi notices, the 2025 law took effect on 2026-05-01, and the 2022 permit regulation and 2020 implementing rules are watched for alignment.
- The cue list is unchanged, so closure questions keep an empty policy block until the level-aware ordering lands. Register: 72 sources, 69 acquired; notice 11. Eval unchanged on every arm.

## 2026-11-02 — Watch works behind the TLS interception; gaps A and B re-checked

- The first live watch run marked nine of ten sources unreachable; the cause was the local TLS interception, not the pages. The checker now honours `SCS_FKB_CA_BUNDLE`, falls back once to `/etc/ssl/cert.pem` on a certificate error and never disables verification. All ten seeded sources now answer 200 and are recorded as unbaselined.
- Gap review repeated live: the national station column lists 2021–2026 news but no 2024 monitoring letter; the Guangdong notice and policy lists do not show 粤农农函〔2026〕208号 on their first pages; the ministry gazette index carries no file list. Nothing new is registered.
- The NSOAS 2021 annual report is recorded as a candidate only: it documents 368 fishery-forecast issues in 2021 but weighs 178 MB for 39 pages, so the size decision stays with the owner.
- Eval unchanged on every arm; make check and the private gate pass.

## 2026-11-02 — Curated source watch and written authority rules

- Added configs/source-watch.yaml with ten authoritative pages (ministry gazette index and four 2025 issues, two Guangdong announcement pages, the Guangdong notice and policy lists, the Hainan 2019 hull announcement and the national station monitoring column), each with an A/B/C tier, publisher and cadence.
- Added src/scs_fkb/watch.py and the `scs-fkb watch` subcommand: read-only GET with a timeout and user agent, body-hash and caching-header comparison, statuses ok/changed/unbaselined/unreachable, JSON report on request, and an offline mode that never opens a socket. It never edits the register or downloads documents.
- Added docs/sources.md: authority tiers, what may enter the register, what may not (news, reposts, aggregators, login-gated pages), version and supersession rules, and why the answer path is not allowed to fetch live.
- Tests cover 200 changed/unchanged, 304, 404, timeout, unbaselined, offline and malformed entries; CI needs no network. Eval unchanged on every arm.

## 2026-11-02 — Spreadsheet parser and the Guangdong/Hainan hull catalogs

- Added `src/scs_fkb/parsers/table.py`: xlsx via openpyxl and xls via xlrd, one page per worksheet, sheet name first and rows joined by ` | `; values as published, no conversion. Registered both formats in the parser dispatch and added openpyxl/xlrd to requirements-dev.txt (requirements.txt already declared them; the venv did not have them).
- Registered `STD-GD-064` (2020 second batch, 83 types), `STD-GD-065` (2021, four types), `STD-HN-066` (2019 small catalog) and `STD-HN-067` (2019 large and medium catalog). The Hainan page lists 附件2 before 附件1 and the file names carry no hint, so the sheets were opened and the names checked before registration.
- Probes: the Guangdong 18 m gillnet question returns the catalog row from `STD-GD-064`; the Hainan small-catalog question returns `STD-HN-066` first. The hull-parameter gap now covers Fujian, Guangdong and Hainan; only Guangxi has no public catalog.
- Eval unchanged at index e4f8d55d7d49, hybrid 10/11, reference 4/4, statistics 2/2, abstention 3/4, jurisdiction 3/3. Register: 71 sources, 68 acquired; standard 15.

## 2026-11-02 — Reference blocks deduplicate per document

- The standard, product and policy blocks now drop identical passages, cap one document at two passages and fill the remaining slot from the next document in rank order. A Hainan question shows POL-HN-059 twice at most plus POL-HN-058; the product block for Q-E08 shows MUR twice plus OLCI.
- `lookup()` is unchanged, so the evaluation reference arm still reads the raw ranking: reference 4/4, jurisdiction 3/3, statistics 2/2, hybrid 10/11 and MRR 0.45 all hold.

## 2026-11-02 — Jurisdiction-aware ranking and answer assembly

- The policy reference collection now carries a jurisdiction code per document, indexes document titles with a title boost, and stably puts a named province first; the main index and its vectors are untouched.
- `answer_question` accepts optional extra hits: a province question leads with the province sentence and its citation, and a question the main index would have abstained on is answered from the province evidence with reason `jurisdiction_evidence`. National or unrelated sentences are filtered out of province answers.
- Behaviour: 海南省2026年休渔时间和海域？ now answers 2026年5月1日12时至8月16日12时 with [POL-HN-059 §一、休渔时间]; 广西 leads with POL-GX-060; 广东 consequence questions lead with POL-GD-061 §四; the national closure question keeps its POL-CLOS-015 §三 answer and an empty policy block.
- Evaluation: a separate jurisdiction section scores J1/J2/J3 at 3/3. The main arms are unchanged at index e4f8d55d7d49, hybrid 10/11, MRR 0.45, abstention 3/4, two false refusals, reference 4/4 and statistics 2/2. The three questions are same-set calibration, not a held-out split.

## 2026-11-02 — Fujian hull catalogs registered; hull parameters become answerable

- Added `POL-FJ-063` (闽海渔〔2025〕4号, 2025-01-17) and its three docx catalogs: `STD-FJ-064` (sixth batch), `STD-FJ-065` (seventh batch) and `STD-FJ-066` (Pingtan-only). The docx suffix dispatch from the previous task reads them, and the parameter tables come out as text: 船型名称, 船长, 型宽, 型深, 主机功率, 总吨位, 版权单位.
- The hull-parameter gap closes for Fujian only. Guangdong still publishes xlsx attachments and Hainan an image-only scan, so those questions stay uncovered and the notes say so.
- Gap re-checks recorded, not filled: the 2024 monitoring letter still has no public full text and the gazette issue pages remain script shells; the Guangdong 2026 work plan is cited by five municipal notices but none carries the provincial text, so `POL-GD-061` stays municipal.
- Probe: the 31.7 m GRP jigging-vessel question returns `STD-FJ-065` first with the parameter row; the Guangdong batch-count question returns no number and the main answer abstains. Eval unchanged at index e4f8d55d7d49, hybrid 10/11, MRR 0.45, reference 4/4, statistics 2/2, abstention 3/4. Register: 67 sources, 64 acquired; standard 11, notice 10.

## 2026-11-02 — Reference collections dispatch by suffix; hull evaluation method registered

- Fixed a loader defect: the reference-collection loader passed html for every file that was not a pdf, so a docx source failed with text.encoding. It now dispatches on the suffix (pdf, docx, ofd, doc, html fallback), and a new test builds a docx collection document and asserts the lookup reaches it.
- Registered `STD-HULL-062`, 渔船标准船型评价方法（试行） (annex to 农办渔〔2017〕5号, 2017): the three-level evaluation, the naming method and the application forms for marine capture vessels over 12 m. It is the method the provincial catalogs implement and the Hainan 2019 announcement cites it by number.
- Recorded the catalog block in docs/corpus.md 5g: Guangdong announces 83 types in the 2020 second batch and 4 in 2021 with xlsx attachments and navigation-heavy pages, Hainan announces 7 large and 15 small types in 2019 with an image-only notice PDF and two xls catalogs, Guangxi has no public catalog, and the pipeline has no xlsx parser, so no catalog is registered and hull-parameter questions stay uncovered.
- The Guangdong batch-count probe returns the evaluation method but no number, so it abstains rather than fabricating; the evaluation-method probe returns `STD-HULL-062` first. Eval unchanged at index e4f8d55d7d49, hybrid 10/11, MRR 0.45, reference 4/4, statistics 2/2, abstention 3/4. Register: 63 sources, 60 acquired; standard 8.

## 2026-11-02 — Hainan joins the register and the 2026 closure implementations land

- Added `POL-HN-058` (海南省实施《中华人民共和国渔业法》办法, 2013 revision, 41 articles, in force since 2014-01-01) and the three 2026 closure implementations: `POL-HN-059` (海南省2026年伏季休渔告知书, 2026-04-24), `POL-GX-060` (广西2026年海洋伏季休渔管理工作通知, 2026-04-22) and `POL-GD-061` (汕头市2026年海洋伏季休渔通告, 2026-04-28, municipal).
- Hainan had no document at all; the 2008 page on the same portal is marked 已修改, so the in-force 2013 revision is registered instead. Guangdong is the honest asymmetry: the provincial 2026 work plan 粤农农函〔2026〕208号 is cited by municipal notices but not published on the provincial site, so the Shantou notice is registered as municipal and labelled.
- The four documents join the policy collection; cues were narrowed to 海南, 广西 and 广东 so a national closure question no longer pulls provincial notices into its reference block.
- Probes: the Hainan, Guangxi and Guangdong questions all return their province document within the top three, but not always first, because the notices share the closure vocabulary; closure question keeps its §三 main answer and an empty policy block. Eval unchanged at index e4f8d55d7d49, hybrid 10/11, MRR 0.45, reference 4/4, statistics 2/2, abstention 3/4. Register: 62 sources, 59 acquired, 3 candidates; regulation 15, notice 9.

## 2026-11-02 — 2020 fishery-monitoring circular registered, 2024 letter recorded as unpublished

- Added `POL-YJ-057`, 关于通报2020年度渔情监测统计工作情况的函 (农渔科函〔2021〕21号, 2021-04-15, 7 pages, text layer). It documents the annual cadence, the responsible bodies and the data-quality machinery of 渔情监测统计, and is newer than `POL-YJ-052` (the 2017 circular) without duplicating it.
- The 2024 letter (农渔科函〔2025〕87号) is quoted by provincial sites but is not published in full; the ministry gazette index exposes no file list and the national marine forecast portal is a single-page service without a downloadable product document. The 2020 circular is therefore the newest publicly posted text, and Q-M07 stays uncovered rather than being filled with a restatement.
- Registered in the policy collection; the monitoring probe returns `POL-YJ-057` first, Q-M07 still abstains, and the eval is unchanged at index e4f8d55d7d49, hybrid 10/11, MRR 0.45, reference 4/4, statistics 2/2, abstention 3/4. Register: 58 sources, 55 acquired, 3 candidates; notice 6.

## 2026-11-02 — Four ocean-colour terms in the terminology bridge

- Added 水色 → ocean colour, 覆盖周期 → coverage cycle, 重访 → revisit and 幅宽 → swath to `configs/glossary-bridge.yaml` (fifteen terms now). The bridge is a retrieval mapping used by the reference channels, not a translation, and each note says so.
- Before: 海洋水色产品的覆盖周期是多少？ and 海洋水色产品的幅宽与重访周期是多少？ returned an empty product block, because the channel fires on bridged concepts and those words were unmapped. After: both return `STD-HY1-056`.
- Guards held: Q-E08 still returns MUR first, Q-M09 still returns the Chinese page, the four abstention questions answer exactly as before, and the eval is unchanged at index e4f8d55d7d49, hybrid 10/11, MRR 0.45, reference 4/4, statistics 2/2, abstention 3/4.

## 2026-11-02 — Crew management, the Chinese ocean-colour page and the product-channel fix

- Added `POL-CREW-055` (渔业船员管理办法, 2022 revision, 54 articles and four annexes) and `STD-HY1-056` (HY-1C/D 产品能力说明, 国家卫星海洋应用中心). The register now holds fifty-seven sources, fifty-four acquired and three candidates; regulation 14 and fishery_product 4.
- `POL-CREW-055` joined the policy reference collection and answers the minimum-manning question through the existing cues. The Guangdong, Guangxi and Fujian port-and-vessel regulations state crew duties only in principle; this is the national rule with the manning table (附件4) and the captain duty to fill the fishing log.
- The product channel now searches with the bridged English concepts plus the original question, so a Chinese-language document in the collection can rank. `Q-E08` still returns MUR first, `Q-M09` now also expects `STD-HY1-056`, and the reference arm stays 4/4 with the main metrics unchanged.
- Hainan stayed out of the register: the provincial government page carries the 2008 amendment and is marked 已修改, and the national law database serves the in-force 2013 revision only through a script-driven page and a signed attachment this network cannot extract. No superseded text was registered.
- The main index and its baseline are untouched: twenty-nine documents, 703 chunks, index e4f8d55d7d49, hybrid 10/11 with MRR 0.45, abstention 3/4 and two false refusals.

## 2026-11-02 — Period questions lead with the date range

- Period questions (时间/日期/起止/何时/几月/几号/期间, and no implementation word) now search every retrieved hit for a date-range sentence and cite it first; questions asking about implementation keep the implementation-date lead.
- `ask "南海区伏季休渔的起止日期与适用范围是什么？"` now leads with `（三）北纬26度30分至北纬12度的东海和南海海域为5月1日12时至8月16日12时。 [POL-CLOS-015 §三、休渔时间]`; the exemption question keeps its §二 lead.
- Retrieval, reference, statistics and abstention metrics are unchanged: hybrid 10/11, MRR 0.45, two false refusals, 100% citation resolution, reference 4/4, statistics 2/2, abstention 3/4.

## 2026-11-02 — Reference collections and corpus hash correction

- Added the product (five English product documents) and policy (five Chinese governance documents) reference collections, reached through the terminology bridge; the main index, its dense vectors and its gate are untouched at twenty-nine documents, 703 chunks and index e4f8d55d7d49.
- Q-E08 and Q-M09 moved from abstention tests to product-collection questions; the evaluation now reports reference 4/4, statistics 2/2, abstention 3/4 and the unchanged main hybrid 10/11 with MRR 0.45, two false refusals and 100% citation resolution.
- Corrected four corpus hashes (POL-STAT-050, POL-STAT-051, POL-YJ-052, POL-VMS-053) that had recorded a concatenation of hex instead of the file hash; the e-certificate concatenated hash was re-verified and left as documented.

## 2026-11-02 — Current statistical-governance and monitoring documents

- Currency check before acquiring: the 2021 fishery statistics survey system had expired, so `POL-STAT-051` registers the 2024 text (国统制〔2024〕120号, valid to June 2027); the 2010 work rules show no repeal; the 2024 monitoring letter exists but has no public full text, so `POL-YJ-052` is the 2017 circular with the caveat; the 2019 distant-water measures replaced the 2014 version and stay in force; the 2025 e-certificate standards are current.
- Added `POL-STAT-050` (work rules), `POL-STAT-051` (2024 survey system), `POL-YJ-052` (2017 monitoring circular), `POL-VMS-053` (distant-water monitoring measures) and `STD-ECERT-054` (three e-certificate standards, 61 pages).
- SC/T 9403-2025 was already held inside `STD-SC-042`, so it was not registered twice. The register now holds 55 sources, 52 acquired and 3 candidates; regulation 13, notice 5 and standard 7.
- Near-shore VMS definitions and a data-sharing metadata rule remain uncovered; Q-M02, Q-M06 and Q-M11 stay out of reach.

## 2026-11-02 — Five documentation sources for the remote data stack

- Added `STD-MUR-045` (MUR 0.01° SST product page, CC BY 4.0), `STD-OLCI-046` (EUMETSAT OLCI marine handbook, 41 pages), `DICT-GFW-047` (apparent fishing effort versus fishing events), `DICT-GFW-048` (GFW Events API documentation, Apache 2.0) and `STD-CMEMS-049` (CMEMS GLOBAL_MULTIYEAR_PHY_001_030 user manual, Issue 1.7).
- The register now holds fifty sources, forty-seven acquired and three candidates; `fishery_product` went from zero to three and `data_dictionary` from six to eight.
- These documents describe the data the remote forecasting project actually runs on, so the knowledge base can explain product resolution, latency and field semantics. They are registered but not indexed: adding them to the pipeline and turning Q-E08/Q-M09 into answerable questions is a separate task.
- The GFW FAQ page states only site Terms of Use, so its licence is recorded as unknown and it stays local like every other acquired document.

## 2026-11-01 — Local statistics channel

- The 3,126-row yearbook indicator table now sits under the data root and is queryable locally: `scs-fkb stats "2019年南海区海洋捕捞产量"` returns the published South China Sea row with its edition and table citation, and `stats` also answers region, gear, vessel, population, value and port questions.
- Two source dimensions are genuinely absent and the channel says so: production is not published by operation type, and vessel counts carry no sea area. It returns the rows that exist and appends one explicit note instead of substituting a dimension.
- The evaluation scores the two statistical questions as a separate channel metric (2/2) next to the reference metric; the main hybrid numbers stay at 10/11, MRR 0.45, abstention 5/6, two false refusals and 100% citation resolution.
- Values stay local: the public tree carries only the schema, the query layer and a synthetic fixture.

## 2026-11-01 — M2 retrieval comparison and hybrid adoption

- Compared four arms on the same instrument: BM25 8/11, BM25 plus lexicon 9/11, dense-only 8/11 (bge-small-zh, 512 dimensions, P95 16 ms) and hybrid 10/11 (MRR 0.45, P95 17 ms); every arm keeps abstention at 5/6, two false refusals and 100% citation resolution.
- Adopted weighted reciprocal-rank fusion with BM25 weight 2.0, dense weight 1.0 and the single surviving lexicon group; the lexical gate stays the only abstention signal because cosine scores do not separate out-of-scope questions.
- The dense index is local only: 703 vectors in the data root, model cached under the data root, nothing published and CI still runs without a model.
- The two remaining misses (Q-M10, and the reference-only definitions aside) are recorded; M2 closes with a measured baseline rather than a claim.

## 2026-11-01 — Terminology bridge and reference channel

- Added `configs/glossary-bridge.yaml`, a project-authored mapping of five Chinese statistical terms to the CWP English concepts; it contains no CWP text.
- Added a reference channel that reads the three registered CWP pages, verifies their hashes against `configs/cwp-handbook.yaml` and answers concept queries, so Q-E05 and Q-M04 now return a standard definition passage (2/2).
- The main index is untouched: still twenty-nine documents, 703 chunks, anchor-level Recall@5 8/11, abstention 5/6, two false refusals and 100% citation resolution.
- Added the `define` command, which prints the CWP passages for a Chinese term such as 上岸量.

## 2026-11-01 — International definitions and species list registered

- Acquired `STD-CWP-043`: three CWP Handbook pages (catch and landings, fishing effort, ISSCFG gear classification) that supply the international definition of catch, landings and effort; the domestic yearbooks still state no Chinese official definition for landed weight or effort.
- Acquired `STD-ASFIS-044`: the ASFIS 2026.1 species list, 13,965 records with 3-alpha codes and 2,695 Chinese names, as a reference dictionary.
- Both carry the FAO CC BY-NC-SA 3.0 IGO licence and stay local; neither enters the M1 index. A dry run adding the CWP pages lowered abstention from 5/6 to 4/6 without improving Chinese-question recall, so a bilingual term layer is the precondition.
- The register now holds forty-five sources: forty-two acquired and three candidates.

## 2026-11-01 — Public corpus and anchor-level baseline

- Indexed all twenty-nine public sources into 703 chunks: added PDF and legacy DOC adapters and stopped dropping table-of-contents and page-furniture lines.
- Replaced document-level scoring with section and page anchors in `configs/eval.yaml`: eleven questions with one to three anchors and six abstention tests.
- Added a title field boost to BM25 and recalibrated the evidence gate on the larger corpus: anchor-level Recall@5 8/11, abstention 5/6, two false refusals and 100% citation resolution.
- Classified the three misses (Q-E10, Q-M10, Q-M12) as vocabulary mismatch between question and article, which is the recorded motivation for dense retrieval.

## 2026-11-01 — M1 extractive prototype evaluated

- Restored the pipeline modules and added HTML, DOCX and OFD parsers, so `POL-STD-010`, `POL-LAW-009` and `POL-SPEC-041` parse into 178 chunks with article and page anchors.
- Replaced the keyword-based refusal with an evidence gate: the top chunk must reach a BM25 score floor and share three distinct query tokens, and every refusal reports a reason.
- Ran the draft question set: document-level Recall@5 of 10/10 on the ten policy questions, abstention on 5/6 out-of-scope tests, one false refusal and 100% citation resolution.
- Corrected the expected evidence of Q-E10 to the two gear standards and recorded the ten-question M1 subset and the six abstention tests.
- Documented the baseline as document-level only: answer correctness needs reviewed gold answers and stays with WP5.

## 2026-11-01 — Repository description refreshed to the accepted corpus state

- Rewrote the README status to the accepted corpus: forty-three registered sources (forty acquired, three candidates), nine yearbook editions over 838 files, six national bulletins, the China Statistical Yearbook 2026, twenty-four legal and technical documents and seventeen SC/T standards over 295 pages; the 3,126-row core CSV stays local.
- Added a corpus summary table and recorded the three gaps and the accepted sufficiency review (ten answerable, six partial, eight abstention tests).
- Replaced the stale "M1 deferred until corpus sufficient" wording: the corpus is sufficient, so M1's start is now an owner decision.

## 2026-11-01 — Logbook candidate closed; document references corrected

- Closed `OPS-LOG-002`: articles 50-53 of the permit regulation, the approved-operation block `OPS-FORM-036` and SC/T 9460-2025 cover the record fields and the reporting duty, so no separate acquisition is planned. The register now holds forty-three sources: forty acquired and three candidates, all deferred.
- The question table no longer cites the four removed environment and fishery-product sources: six questions are marked "none registered" and act as abstention tests, and the three logbook questions point at the permit regulation and the approved-operation block.
- Corrected the yearbook file count from 839 to 838 and refreshed the plan, the corpus summary and both READMEs to the 3,126-row table and the three-candidate register.

## 2026-11-01 — 2025 sample folded into the long-table schema

- Rebuilt the local core table so the 2025 data year uses the same regions, sea areas, indicators, units and derived rows as 2017–2024: 3,037 rows for 2017–2024 plus 89 harmonised rows for 2025, 3,126 in total.
- Moved the 54 transcribed 2025 values outside the five indicator families (output and aquaculture totals, the port total, breed farms, household/township/village counts and three other sea areas) into a local extras file.
- Added the three derived South China Sea rows for 2025 (published 2,626,036; three-province subtotal 2,626,036; difference 0).
- Added Fujian to the region values in `configs/statistics.yaml` as a background row for the published South China Sea column in data years 2017–2020.
- Every row now validates against the schema dimensions; the 2017–2024 prefix is unchanged.

## 2026-11-01 — Seven undigitised SC/T standards excluded from the project

- Seven in-scope standards have no public text on the national standards platform: SC/T 0002.21, 0002.22, 0002.24, 0002.25 and 0002.26 (2001 vessel coding series), SC/T 8002-2000 (vessel terminology) and SC/T 9010-2000 (port design). The only official copies found are paid publications.
- On owner instruction they are excluded from the project: removed from `configs/sc-standards.yaml` and no longer tracked as a gap in the register note, so the series records only the seventeen standards the project holds.
- No other count changes: the register still holds forty-four sources, and the series still covers seventeen standards and 295 pages.

## 2026-11-01 — SC/T standards in scope acquired; out-of-scope downloads discarded

- Catalogued the SC/T series from the national standards platform filing interface: 977 records, 809 current.
- Applied the project scope (marine capture, gear and mesh, vessel management data, fishing ports, fishery statistics and surveys, resource surveys, terminology): 24 standards match, 17 have a public text and are held as image-only reference PDFs (295 pages), and 7 have no public text on the platform (vessel coding and port design, 2000-2001).
- Deleted the out-of-scope downloads, 695 standards covering aquaculture, feed, disease, processing, hull construction, ship equipment, gear-material testing and freshwater surveys; SC/T 9460-2025 stays registered as OPS-STD-035 and is not duplicated in the series.
- Registered `STD-SC-042` as a series entry with the public catalog `configs/sc-standards.yaml`; the register now holds forty-four sources: forty acquired and four candidates.

## 2026-11-01 — 2026 closed-season special-permit notice registered

- Registered `POL-SPEC-041` from the owner-supplied OFD, which is byte-identical to the ministry attachment `P020260424354196891178.ofd` (SHA-256 `b383ea35…`); the file has 22 pages and its text layer extracts without OCR.
- The notice creates the 2026 South China Sea permits: Sthenoteuthis oualaniensis for Guangxi (36 vessels, 2,500 t, 20 June to 5 August, mask net 35 mm, Beihai Nanwan port) and Hainan (70 vessels, 5,000 t, 1 May to 15 August, mask net 35 mm, Sanya Yazhou, Qionghai Tanmen and Danzhou Baimajing central ports), plus 26 Hainan auxiliary vessels landing at those ports and the Sansha West quay. Its operation-type permits cover only the Yellow and East China Seas.
- The register now holds forty-three sources: thirty-nine acquired and four candidates. The corpus type table was corrected to sixteen yearbooks, four notices and four standards, and the plan, READMEs and tests were refreshed in the same change.

## 2026-11-01 — Environment and fishery-product sources excluded; no duplicate registered

- Removed the four environment and fishery-product candidates (sea surface temperature, chlorophyll/current/wind, fishing-ground bulletin, historical season record) from the register on owner instruction; the fishery_product type stays defined with zero sources.
- Audited every remaining gap: logbook fields are partly covered by the permit regulation and the approved-operation form, port classes by the 2018 plan and the 2025 list, the definitions by the two acquired definition sources; the complete logbook field list, landed weight and effort definitions, metadata rules and the remaining 2025 tables have no public source or are extraction work, so nothing new was added and no acquired source was duplicated.
- The register now holds forty-two sources: thirty-eight acquired and four candidates.

## 2026-11-01 — Sufficiency review accepted for the P1 scope

- Reviewed the 24 draft questions against the register: 10 answerable, 6 partially answerable, 8 not answerable. All eight blocked questions point at deferred P2 candidate sources, so nothing in the P1 scope is blocked.
- Three questions will be reworded to match what the yearbooks publish: production by operation type, the landed-weight and effort definitions, and the combined production-and-vessel-count question.
- The eight blocked questions remain abstention tests; the remaining work is the port-classification mapping and the candidate close-out.
## 2026-11-01 — Core CSV extended to data year 2025

- Appended the 140 verified 2025 rows to the local core CSV: 3,037 rows for 2017-2024 plus 140 for 2025, same 20-column layout, 2017-2024 untouched.
- Cross-checked the 2025 block against China Statistical Yearbook 2026 table 12-15: twelve cells match exactly, including the identity that the national yearbook's marine capture equals marine capture plus distant-water output in the fisheries yearbook.
- The 2025 block is partial: species, power and length bands, marine capture value and the remaining tables still need extraction from the scan.
## 2026-11-01 — 2026 yearbook sampled: table list and six tables

- Mapped the 166-page scan to a table list covering the seven parts and the appendices, with printed-page locators and a note on the new part/section layout introduced by the 2025 edition.
- Transcribed six tables for the national total and Guangdong, Guangxi and Hainan: output, capture by sea area, capture by gear, capture vessels by operation type, fishing ports and fishery population (140 non-empty cells, values local only).
- Consistency checks: 23 of 24 identities hold (culture plus capture equals output, gear sums equal capture, port classes sum to the port total); the one skip is a blank source cell for Guangxi stow-net vessels. The South China Sea column equals the three-province sum exactly.
- Limits: single reader, no second-person check yet; the species breakdown and remaining tables are the next extraction batch.
## 2026-11-01 — Scanned 2026 yearbook registered

- Registered STAT-YB-2026, the 166-page scan of the 2026 fisheries yearbook (data year 2025), supplied by the owner.
- The file has no text layer, so the register records it as provenance only: no table is extracted and the coverage matrix still ends at data year 2024 until OCR or manual entry is done.
- Yearbook editions now nine, covering data years 2017-2025; the register holds forty-six sources, thirty-eight acquired.
## 2026-11-01 — Production definitions acquired

- Registered the 2024 fisheries yearbook appendix 3 (渔业统计指标解释) as DICT-STAT-013: a 16-page extract from the owner-supplied yearbook PDF, covering the product concept, the reporting unit, the fresh-weight basis, the culture-versus-capture rule, and capture production by sea area and gear group.
- Registered the national yearbook chapter-12 notes as DICT-STAT-040: the headline water-product definition used by the National Bureau of Statistics, without a sea-area or gear split.
- The definition candidate is closed; the register now holds forty-five sources, thirty-seven acquired, and the inventory records what each definition covers.
## 2026-10-31 — Issuing notices attached; classification standard registered; duplicates removed

- Registered the 2013 minimum-mesh notice as POL-GEAR-016, which ties the two mesh annexes and the permit form to one instrument: in force 2014-06-01, three sea areas, measurement under GB/T 6964—2010, earlier 2003 notice repealed.
- Registered GB/T 5147—2026 (fishing-gear classification, naming and codes), effective 2026-09-01, replacing the 2003 edition.
- Corrected the annex metadata: publisher 农业部 and year 2013 for the two mesh standards and the form; the port recognition list is dated 2025 and is a proposal open for comment until 2025-01-22.
- Removed duplicates: three annex copies inside the older notice package, and a byte-identical duplicate of a 2022 yearbook table; the 2022 edition manifest was regenerated and the register records the new hash.
- The register now holds forty-four sources, thirty-five acquired.
## 2026-10-31 — Technical supplements registered for the definition, operation and port gaps

- Registered the minimum mesh-size annexes for permitted and transitional marine capture gear, the SC/T 9460—2025 marine capture information sampling survey standard, the approved-operation form with its filling instructions, the central and first-class port recognition list, and the national coastal fishing-port construction plan for 2018–2025.
- Added the `plan` corpus type for official plans and construction layouts; the register now holds forty-two sources, thirty-three acquired.
- Kept the official ministry PDF edition of the fishing-permit regulation as a format copy beside the registered HTML; its articles 50–53 carry the logbook obligation.
- The standard series answers the operation-type and gear-classification questions in part and points to GB/T 5147—2003; the 2018 port plan supplies the port baseline the yearbooks lack for data years 2018–2019.

## 2026-10-31 — Fujian regulations added; legal corpus consolidated

- Registered the Fujian measures implementing the Fisheries Law (2019 amendment, five chapters, 61 articles) and the Fujian fishing-port and fishing-vessel regulations (2010 amendment, seven chapters, 46 articles), both owner-supplied and hash-verified.
- The legal corpus now spans the national level plus Guangdong, Guangxi and Fujian: twelve documents covering one law, ten regulations and one notice.
- Removed the duplicate People's Daily copies of the Fisheries Law (electronic edition, page-11 PDF and municipal reprint); the registered DOCX is the single retained text.
- Removed the agricultural statistical reporting-system summary, which carried no fisheries indicator definitions, so the data-dictionary type is again represented only by open candidates.
- The register now holds thirty-six sources: twenty-seven acquired and nine candidates; the README, plan, inventory and tests were refreshed in the same change.

## 2026-10-31 — National bulletin series completed

- Registered the 2020, 2021, 2022, 2023 and 2024 national fisheries economic statistical bulletins, joining the already registered 2025 bulletin.
- The series now covers data years 2020–2025 with official national totals; values stay local and only metadata is published.
- Each page was verified by title, publication date and the published total output figure.

## 2026-10-31 — China Statistical Yearbook 2026 registered

- Registered the China Statistical Yearbook 2026 Excel set (1,318 files, Chinese and English editions) as an internal statistical source with a per-file manifest and manifest hash.
- Its aquatic-production table extends national and provincial totals to data year 2025, including marine capture and aquaculture splits for coastal provinces.
- The Excel set does not carry the printed indicator explanations, so the definition source remains open.

## 2026-10-31 — Statistical bulletin and reporting system registered

- Registered the 2025 national fisheries economic statistical bulletin (data year 2025) as a public source; it gives national totals only and does not replace the yearbook editions.
- Registered the 2026 agricultural statistical reporting system summary from the National Bureau of Statistics as a reference dictionary.
- Recorded that the reporting-system summary does not define fisheries production, landed weight or fishing effort, so the definition source remains an open candidate.

## 2026-10-31 — Legal corpus registered

- Registered the Fisheries Law text as the owner-supplied DOCX of the official 人民日报 2026-02-25 publication, replacing the e-paper HTML as the citation copy while keeping the HTML, the page-11 PDF and the reprint as provenance.
- Added five national regulations (implementing rules, vessel inspection, resource levy, permit rules, seasonal closure) and four provincial regulations (two Guangdong, two Guangxi) to the corpus.
- Every legal source now carries a jurisdiction (national, guangdong or guangxi), a SHA-256 and its revision history; article counts were verified from 90 down to 4 notice sections.

## 2026-10-31 — Fisheries Law replaced with the official publication

- Replaced the municipal reprint of the Fisheries Law with the official 人民日报 publication of 2026-02-25 (page 15), which carries 主席令第六十三号 and the 新华社 release of the 2025-12-27 revision.
- Verified the text as seven chapters and 90 articles, with the 2025-12-27 revision line and the 2026-05-01 effective date; recorded the new SHA-256.
- The canonical npc.gov.cn page returned HTTP 403 from this network, so the newspaper publication is the citation copy; the reprint is retained in the data root.

## 2026-10-31 — Corpus register closed

- Dispositioned the nine remaining candidates: `DICT-STAT-013` and `OPS-LOG-002` are marked to acquire, the other seven are deferred with a recorded reason; removed the superseded `OPS-STAT-001`.
- The register now holds 20 sources: 11 acquired and nine candidates with an explicit disposition.
- Confirmed against the 838-file inventory that the 2019 and 2020 editions contain no infrastructure table, so the 2018–2019 port gap cannot be filled; accepted the 2024 vessel-length gap instead of using a non-comparable table.
- Documented the 2025 edition table reorganisation and that no edition publishes capture production by operation type.
- Attempted to replace the Fisheries Law reprint with the official standard text; the official source was unreachable on 2026-10-31, so the reprint remains and the attempt is recorded in the register and the run report.

## 2026-10-31 — Core CSV built and validated

- Built a 3,037-row local long-table CSV for capture, vessels, population, marine capture value and coastal ports (data years 2017–2024).
- Added `power_band` and `length_band` to the public schema; values remain local and are not published.
- Validated all source hashes and spot values; gear and vessel sums reconcile to their totals.
- Corrected the South China Sea boundary: the published column includes Fujian in 2017–2020 and excludes it from 2021 onward.

## 2026-10-31 — Yearbook corpus registered

- Registered eight official/authorized China Fisheries Statistical Yearbook editions (2018–2025, data years 2017–2024) as internal, local-use sources.
- Replaced the seven topic categories with eight corpus types; removed papers/reports from the register and mapped bulletins and data dictionaries to the new types.
- Added the public statistics schema and the core coverage matrix; values remain local and are not published.
- Recorded coverage gaps: coastal ports for 2018–2019 and the vessel-length proxy for 2024.

## 2026-10-31 — Return to data preparation

- Reverted the M1 pipeline implementation and its status claims; the public tree contains no pipeline code.
- Kept the three-document register and acquisition evidence; removed local processed chunks and archived the M1 run report.
- Current phase: verify authoritative sources, define the South China Sea nearshore boundary and build an indicator coverage matrix. Pipeline planning waits for sufficient data.

## 2026-10-31 — First P1 corpus acquired

- Registered three official public documents: the Fisheries Law (2025 revision, effective 2026-05-01), the 2023 seasonal closure notice and the 2022 fishing permit regulation.
- Recorded licence, sensitivity, SHA-256 and data-root-relative locations; the payload stays outside the repository.
- Updated the corpus inventory and tests; parsing and indexing are deferred until the corpus matrix is sufficient.

## 2026-10-31 — Public repository normalization

- Adopted a no-version release policy: no tags, no GitHub Releases and no semantic versions.
- Added bilingual entry points, a Chinese project scope and Chinese summaries for key documents.
- Moved community files into `.github/` and added governance, support, ADR, glossary and style-guide documents.
- Moved local data and run roots outside the repository; the public tree contains no data or run directories.
- Hardened the public-tree check and CI, and enabled repository security settings.

## 2026-10-30 — Framework and project plan

- Added the overall architecture: layers, components, data flow, data contracts, runtime and quality attributes.
- Added the project plan: work packages, milestones, dependencies, roles, schedule, quality gates and risks.
- Added the evaluation protocol: question set, metrics, baselines, targets and reporting.
- Replaced the versioned changelog with this dated project log.
- Rewrote the project introduction to focus on scope, framework and plan.
- Removed the version-specific release presentation; the project is introduced through the README and project documents.

## 2026-10-30 — Initial public repository

- Published the public repository with project scope, corpus register, draft evaluation questions, data policy, licences, citation metadata, CI and community files.
- Established the rule that data, indexes, run artifacts, state databases and secrets are not published.

## References

- [Project scope](../PROJECT.md)
- [Architecture](architecture.md)
- [Project plan](plan.md)
- [Evaluation](evaluation.md)
- [README](../README.md)

## 2026-11-05 — Coverage-check calibration

- Added `mode: section` to the deterministic coverage check: every term must occur in cited sentences sharing one source section; `all` and `any` are unchanged.
- Audited all 60 gold points. 17 use `section`; 7 check-term sets were replaced with source-exact wording; 3 full-width/space cases are handled by NFKC/whitespace folding; 5 anchor gaps are documented and left for a separate decision.
- No question, gold point, point count (60), anchor count (31), abstention count (11) or split membership changed. Private audit: `runs/P09-EVAL-134/audit.md`.

## 2026-11-05 — Anchor-gap review

- Resolved the five anchor gaps from the coverage calibration. Added the supporting sections for Q-M03, Q-M12, Q-M17 and Q-O03; corrected Q-E10 point 1 to remove the unsupported `更严格` clause.
- Added `mode: document` for compound points spanning sections of one regulation. Counts stay 31 anchors / 11 abstention / 60 points; questions and split membership unchanged.
- Private audit: `runs/P09-EVAL-135/audit.md`.

## 2026-11-06 — SCS-FKB refactor governance baseline

- Froze `main` at `f038cbd` as the refactor baseline: 63 registered sources, 28 indexed documents, 785 chunks, index `20910f0964df`, 48 evaluation questions (33 dev + 15 test), 340 passing tests and 2 skipped tests. No tag or release was created.
- Cancelled the paused B1 task and kept its branch and worktree at `0841f56` as reference only. The approved plan does not merge B1.
- Adopted source schema v4: A/B/C/D authority tiers, `non_official` level, `licensed` licence with an authorisation note, and explicit `provenance`, `effective`, `quality`, `supersedes`/`superseded_by` and `license_note` records. The loader derives v4 defaults for legacy entries without changing ids or hashes; `scripts/migrate_v4.py` writes the derivation audit.
- Adopted the [RAG standard](rag-standard.md) and ADRs [0005](adr/0005-two-plane-evidence.md), [0006](adr/0006-llamaindex-lancedb-bge.md), [0007](adr/0007-controlled-web-evidence.md) and [0008](adr/0008-playbooks-and-terms.md): canonical evidence stays versioned and reproducible, live web evidence is ephemeral, labelled and never auto-ingested, and playbooks/terms carry the internalisation layer.
- Recorded the P10-GOV-136 → P10-EVAL-142 sequence in [plan.md](plan.md). The next task is P10-ING-138 (originally scoped as P10-ING-137): Docling/trafilatura adapters, hierarchical chunking and incremental snapshots.

## 2026-11-06 — Ingestion v2 snapshots and hierarchical chunks

- Added a parallel `src/scs_fkb/ingest_v2/` path: content-addressed snapshots for all 63 acquired sources (2,211 files, 142 MB), loader adapters with legacy fallbacks, parent/child chunks, and an incremental v2 manifest under the local data root.
- The 28 configured main documents build into 745 parent and 785 child chunks with 0 lost page/section anchors against the v1 store. A second build skips all 28; a changed source rebuilds only itself; a removed document is dropped; a parse failure is quarantined.
- Registered HTML/PDF/DOCX keep the legacy parsers so anchors are preserved; Docling and trafilatura are optional fallbacks listed in `requirements-rag.txt` and are not required by CI. The v1 store, index, answer path and evaluation set are unchanged.
- Private report: `runs/P10-ING-138/build.md`.

## 2026-11-06 — Retrieval v2: LanceDB index and regression

- Built a parallel LanceDB index over the 785 v2 child chunks with `BAAI/bge-small-zh-v1.5` (512 dims): index `23e933753e22`, 98 s build, 4.49 GB peak RSS, 0.8 s no-op rebuild.
- Added `src/scs_fkb/index_v2/` (LlamaIndex vector-store adapter, manifest, per-document delete/add) and `src/scs_fkb/retrieve_v2/` (BM25 + dense RRF, sensitivity/authority/level/effective-date filters, router, optional BGE reranker).
- Regression on the 31 anchored questions: no-rerank dev 19/19 (MRR 0.6816), test 12/12, abstention 8/11, P95 16 ms; the optional reranker scores 29/31 (MRR 0.8360) and P95 2.27 s, so it stays disabled by default until calibrated.
- The v1 index, answer path, evaluation set and public boundary are unchanged. Private reports: `runs/P10-IDX-139/build.md` and `runs/P10-IDX-139/regression.md`. Next task: P10-WEB-140.

## 2026-11-06 — Ephemeral web evidence plane

- Added `src/scs_fkb/web_v2/`: SearXNG JSON provider with DuckDuckGo fallback, allowlist-only results, HTTPS fetch with trafilatura/PDF extraction, TTL-aware WebEvidence cache, trigger rules and a promotion draft that never writes the register.
- Smoke-tested 20 freshness queries: 13 returned allowlisted evidence (32 records), 75 non-allowlisted results were dropped and 5 provider failures were recorded explicitly. TTLs are 7 days for warning/status, 30 for rule, 90 for definition/identification and 365 for statistics/history.
- The generic `gov.cn` fallback is tier C and labelled `地方政府网站（层级待核）`; specific central/provincial domains remain A/B. The v1 web-card path, answer path, corpus register and evaluation set are unchanged.
- Private report: `runs/P10-WEB-140/smoke.md`. Next task: P10-KB-142.

## 2026-11-06 — Knowledge internalisation: playbooks, terms and provision facts

- Added 15 approved playbooks with 32 steps under `configs/playbooks/`; every step cites an approved fact and every source is in the register. The validator rejects unknown, draft or stale facts.
- Expanded the terminology map to 150 entries: 116 approved (standard term occurs in the indexed corpus) and 34 draft. The existing 24 approved terms are unchanged.
- Generated 120 draft provision facts from the indexed corpus, each with verbatim evidence and source hash; the fact layer is now 200 (80 approved + 120 draft). The generated facts are section-level review candidates, not approved values.
- Added `scripts/check_playbooks.py` and `scripts/weekly_update.sh`; the weekly report runs source currency, offline watch, facts, terms, playbooks and gap checks without downloading, ingesting or editing the register.
- Checks: facts 200/80/120, 0 errors; terms 150/116/34, 0 errors; playbooks 15/15, 32 steps, 0 errors. Private reports: `runs/P10-KB-142/checks.md` and `runs/P10-KB-142/weekly.md`. Next task: P10-ANS-143.

## 2026-11-06 — Local answer service v2 and Web UI

- Added `src/scs_fkb/service_v2/`: `AnswerService`, Pydantic schemas, FastAPI `/v1/query`, `/v1/sources`, `/v1/playbooks`, `/v1/feedback`, health endpoints and a server-rendered Jinja2 UI.
- The composer uses v2 hybrid retrieval without the reranker, the calibrated extractive answer, approved fact leads, playbook blocks and optional labelled web evidence. Citations are validated before returning; invalid citations become an abstention.
- The service defaults to `127.0.0.1:8765`; `SCS_FKB_API_KEY` enforces `X-API-Key`. Feedback is appended to `$SCS_FKB_RUN_ROOT/feedback.jsonl`; nothing is written to the public tree.
- Added `docs/interface.md` and `configs/interface.yaml`; added optional FastAPI/uvicorn/Jinja2/python-multipart dependencies to `requirements-rag.txt`.
- 20-scenario report: 19 answered, 1 clarification, 19 cited answers, 16 expected-document hits, median 22 ms, 0 web calls. Private report: `runs/P10-ANS-143/scenarios.md`. The v1 CLI/answer path is unchanged. Next task: P10-EVAL-145.

## 2026-11-06 — Evaluation v2 and regression gate

- Added `configs/eval-v2.yaml`: 120 questions (80 dev reviewed facts, 30 draft provision test facts, 10 test abstention cases), generated deterministically by `scripts/build_eval_v2.py`.
- Added `src/scs_fkb/eval_v2/`: RAGAS-compatible deterministic metrics (`faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`, `answer_correctness`, `citation_resolution`, `abstention_accuracy`), per-question rows and a regression gate.
- Real 120-question run: dev correctness 0.8945, citation resolution 1.0000, context recall 0.9875; overall abstention 0.9000; gate passes. Test correctness 0.5820 is report-only because its 30 fact questions are drafts.
- Added `docs/evaluation.md`; the v1 evaluation set and product path are unchanged. No tag or release is created.

## 2026-11-06 — Knowledge review: 20 provisions promoted, terms kept draft

- Reviewed all 120 draft provision facts: 20 promoted to approved with exact evidence and a `review` block, 49 kept draft, 51 marked reject (fragments, OCR, short text, purpose clauses or generic responsibility clauses). Fact layer: 200 total, 100 approved, 100 draft; `facts check` 0 errors/0 conflicts.
- Reviewed all 34 draft terms: none of the standard forms occurs in the registered corpus, so all remain draft with a corpus-gap review note. No term was approved without evidence.
- Reviewed 15 playbooks / 32 steps and corrected six unsupported statements (application materials, permit-term wording, quota rule, fee range, “可以并处” wording).
- Added `docs/review-2026-11-06.md` with the method, promotion IDs, rejection categories, term gaps and playbook corrections. This is an AI-assisted first pass; owner spot-check of the 20 promotions and six corrections is still required.
- No answer, service, retrieval, web, index or evaluation code changed. No tag or release is created.

## 2026-11-06 — Optional SearXNG provider with DuckDuckGo fallback

- Added `FallbackProvider`: a configured SearXNG JSON endpoint is tried first; empty results or provider errors fall back to DuckDuckGo. `SEARXNG_URL` remains optional and CI does not need a SearXNG instance.
- Removed the `safesearch` query parameter from the SearXNG request; the local instance uses the two Chinese engines that work here (`360search`, `sogou`) via `use_default_settings.engines.keep_only`.
- Added `docs/web-search.md` with reproducible local setup, settings, JSON check and the `SEARXNG_URL` smoke command.
- Combined-provider smoke: 20 queries, 15 with allowlisted evidence, 37 evidence records, 84 non-allowlisted drops, 1 explicit PDF timeout, provider label `searxng+ddgs`. The fallback recovered long queries that SearXNG returned empty.
- No corpus, answer, index, facts, terms or playbook changes; no tag or release.

## 2026-11-06 — Reranker calibration: default remains off

- Calibrated the BGE reranker on 31 reviewed anchors: no-rerank 31/31, MRR 0.9301; pure rerank 29/31, MRR 0.8495, P95 2,714 ms; short6 rerank 31/31, MRR 0.9140, P95 2,976 ms; top-1/top-2 preservation 30/31.
- No arm meets 31/31 anchors, MRR at least no-rerank, and P95 <= 500 ms together. The default stays off; `--rerank` remains an optional offline flag.
- Added `docs/reranker.md` with the table, decision, reproduction command and limitations. No retrieval, index, corpus, facts, terms, playbooks or eval code changed.

## 2026-11-06 — External fact/term store rebuilt

- Rebuilt the v1 external store after the knowledge review: 487 documents / 543 chunks (119 cards, 140 notes, 100 approved facts, 116 approved terms, 12 FAQs), chunk index `0b1ecdf229fe`, dense index `6bdf2aad95935994`. Before the rebuild it was 375 documents / 431 chunks / `3259a7694499`.
- Verified external retrieval: `渔业港航行政处罚种类` returns `FACT-POLICY-049` (the promoted fourth-article penalty-types provision); `渔业捕捞许可证` returns `FACT-POLICY-004` and `TERM-001`.
- The corpus store is unchanged at 28 documents / 785 chunks / `20910f0964df`. No code, config, corpus or answer path changed; no tag or release.

## 2026-11-06 — Evaluation docs synced after review

- Re-ran the 120-question evaluation after the 20 provision promotions and external rebuild: overall correctness 0.8026, dev 0.8945, test 0.6189 (up from 0.5820), citation 1.0000, context recall 0.9750, abstention 0.9000. Gate still passes.
- Updated `docs/evaluation.md` and `docs/plan.md`; the 0.5820 figure remains as history in the change notes, not as the current result.
- No code, config, eval set, facts, terms, playbooks or data changed.

## 2026-11-06 — Seven official term sources admitted through A/B

- Register is now **70 sources** (63 + 7), 0 open candidates, with `POL-CREW-083`, `POL-CODE-084`, `POL-ID-085`, `POL-SANWU-086`, `POL-FUEL-087`, `POL-STAT-088` and `POL-RED-089`.
- Captured and SHA-256 hashed seven public A-level pages. The initial `POL-CODE-084` 1562 notice was replaced by the narrower 1100 coding notice after staging showed the 1562 page made an out-of-scope loan question answerable.
- Staging A/B passed: v1 31/31 anchors, dev 19/19, test 12/12, abstention 8/11; v2 dev correctness 0.8945, citation 1.0000, recall 0.9667, abstention 0.9000. Main v1 is 35 docs / 905 chunks / `4d94e7c7f27c`; v2 index `c25ddffea992`.
- Promoted seven terms: 渔业职务船员证书, 渔船编码, 船舶识别号, 涉渔“三无”船舶, 渔业成品油价格补助, 调查对象 and 赤潮. `统计范围` was already `TERM-131`, so `TERM-130` uses `调查对象` from the same official section. Terms are **123 approved / 27 draft**.
- Rebuilt the external store: **494 documents / 550 chunks**, chunk index `9405a2f93585`, dense `f1e02a628271a87b`; all seven new terms retrieve in top 5. Added `docs/term-sources.md`.
- No tag or release; raw HTML stays under the local data root.

## 2026-11-06 — Evaluation docs synced after the term batch

- Post-term-batch 120-question run: overall 0.8069, dev 0.8945, test 0.6319 (0.6189 before the batch), citation 1.0000, recall 0.9667, abstention 0.9000. Gate passes.
- Updated `docs/evaluation.md` and `docs/plan.md`; earlier 0.5820/0.6189/0.8026 figures remain as history.
- No code, config, eval set, facts, terms, playbooks or data changed.

## 2026-11-06 — Batch 2: three sources, five term approvals

- Added `POL-CONS-090` (2024 MOA report on 过度捕捞), `POL-MIN-091` (2018 standalone 最小可捕规格 notice) and `INT-SUS-092` (UN 兼捕 report). The first broad captures (the 2006 action outline and a 64-page gazette PDF) were replaced after staging showed they answered out-of-scope loan and voyage questions.
- Approved 5 more terms: 非法捕捞水产品罪 and 型宽 from existing sources, plus 过度捕捞, 最小可捕规格 and 兼捕. Terms are **128 approved / 22 draft**.
- Staging/main gate: v1 31/31, dev 19/19, test 12/12, abstention 8/11; v2 dev 0.8945, test 0.6327, overall 0.8072, citation 1.0000, recall 0.9667, abstention 0.9000.
- Corpus is 73 sources / 38 documents / **920 chunks** (v1 `0a8d928f2ad2`, v2 `659a7a8c507e`); external store is 499 documents / 555 chunks (`7c58c522ab5c`, dense `05da8d22eab284cc`). All five new terms retrieve in top 5.
- 414 tests pass; private gate 0 hits; no tag or release.

## 2026-11-06 — Batch 3: market, MSY and subsidy terms

- Added `POL-MARKET-093` (State Council Yangtze ban notice, 渔获物上市交易), `INT-MSY-095` (national policy report, 最大可持续产量) and `POL-SUB-094` (Guangdong 2025 subsidy policy, 休渔补贴). Approved two existing-source terms: `数据共享` from INT-SUS-092 and `海温` from POL-OBS-072.
- Terms are **133 approved / 17 draft**. `TERM-145` now uses the source's operational `海温`; `海表温度` and `SST` remain variants.
- Staging/main gate: v1 31/31, dev 19/19, test 12/12, abstention 8/11; v2 dev 0.8945, test 0.6310, overall 0.8066, citation 1.0000, recall 0.9667, abstention 0.9000. The small test/overall movement is within the agreed gate.
- Corpus is 76 sources / 41 documents / **971 chunks** (v1 `43491719734d`, v2 `7d372c2b5f47`); external store is 504 documents / 560 chunks (`c03a133b9f2e`, dense `e06fd4f9fccc5205`). All five new terms retrieve in top 5.
- 414 tests pass; private gate 0 hits; no tag or release.

## 2026-11-06 — Evaluation docs synced after term batch 3

- Post-batch-3 120-question run: overall 0.8066, dev 0.8945, test 0.6310 (0.6319 before), citation 1.0000, recall 0.9667, abstention 0.9000. Gate passes.
- Updated `docs/evaluation.md` and `docs/plan.md`; earlier 0.8069/0.6319 figures remain as history.
- No code, config, eval set, facts, terms, playbooks or data changed.

## 2026-11-06 — Batch 4: ocean product terms, metadata deferred

- Added `POL-OCEAN-096` (satellite fishery-environment product catalog) and approved **叶绿素a浓度**, **海面风场** and **有效波高**.
- Captured `STD-MDR-098` (GB/T 18391.3-2009) for **数据元** and **元数据**, but kept both draft: the 89-page standard pulled generic metadata chunks into Q-M06 and dropped v1 abstention to 7/11. The candidate remains open; no source record or pipeline document was added.
- Terms are **136 approved / 14 draft**.
- Staging/main gate: v1 31/31, dev 19/19, test 12/12, abstention 8/11; v2 dev 0.8945, test 0.6161, overall 0.8017, citation 1.0000, recall 0.9667, abstention 0.9000. Test fell 1.49pp and is report-only under the agreed gate.
- Corpus is 77 sources / 42 documents / **1014 chunks** (v1 `f7a244373e77`, v2 `d007984ae168`); external store is 507 documents / 563 chunks (`458aad366fe1`, dense `91e8ec609611dccb`). The three new terms retrieve in top 5.
- 414 tests pass; private gate 0 hits; no tag or release.

## 2026-11-06 — Evaluation docs synced after term batch 4

- Post-batch-4 120-question run: overall 0.8017, dev 0.8945, test 0.6161 (0.6310 before), citation 1.0000, recall 0.9667, abstention 0.9000. Dev gate held; test is report-only.
- Updated `docs/evaluation.md` and `docs/plan.md`; earlier 0.8066/0.6310 figures remain as history.
- No code, config, eval set, facts, terms, playbooks or data changed.


## 2026-11-07 — Acceptance instrument and baseline

- Added the private 512-question acceptance instrument under the local data root (`eval/acceptance/dataset.jsonl`, `doc-map.yaml`, `manifest.json`) and a deterministic importer (`scripts/import_eval_xlsx.py`). The workbook, the questions and the document map never enter the repository; a rerun produces a byte-identical dataset (`12389b256c4f…`, 256 dev / 256 holdout).
- Added `src/scs_fkb/eval_accept/` and `scripts/eval_accept.py`: protocol metrics (point coverage, citation accuracy, misanswer rate, refusal-with-channel rate, as-of declaration rate, basis accuracy, latency), a 0/0.5/1 band, reason-code clustering, per-question CSV and a Markdown report. Thresholds live in `configs/eval-accept.yaml`; `configs/domain-terms.yaml` supplies generic concept anchors. Points without an anchor are reported as review-needed instead of being scored.
- Document map: 77 instrument documents resolve to 21 full, 10 partial and 46 missing repository documents. 325 of 512 questions reference at least one missing document, which is the dominant gap.
- Baseline (42 documents, 1,014 chunks, index `d007984ae168`, web off, extractive): answer rate 0.4453, point coverage 0.1675, citation accuracy 0.1659, misanswer rate 0.3143, refusal-with-channel rate 0.0286, as-of declaration rate 0.0702, basis accuracy 0.0263, latency mean 17.3 ms / P95 22 ms. The gate fails on all six lines, as expected before the corpus and answer-contract work. 553 of 1,117 required points are judgeable (49.5%).
- Tests: 437 passed, 2 skipped. Ruff clean; public-tree check 225 files. No corpus, index, retrieval, service or answer-path change; no tag or release.

## 2026-11-07 — Acceptance corpus batch: 14 sources captured, 6 indexed

- Added `scripts/capture_source.py` (HTTPS and allowlist by default, `--allow-http` only for allowlisted `.gov.cn` hosts, provenance block, no silent overwrite) with eight offline tests.
- Captured and registered 14 documents the acceptance instrument cites but the corpus lacked: the maritime traffic safety, marine environmental protection, wildlife protection and administrative penalties laws; the vessel registration rule; the banned-gear notice; the criminal filing standard; GB 3097; the Guangdong protected-species list; the Sansha plan; the Qinzhou closure notice; and three peer-reviewed papers. Seven instruments had no official public text and are recorded as exclusions (inspection rules, shellfish-toxin standard, heatwave classification, one paper, the Guangdong closure plan, the Guangxi list).
- Six documents are indexed: the maritime, marine-environment and wildlife laws, the registration rule, the banned-gear notice and the filing standard. Eight stay registered but unindexed with recorded reasons: the administrative penalties law and GB 3097 made refusal tests answerable, the papers are B-tier reference material, the Sansha plan is out of scope, the Qinzhou notice outranked the national closure notice and the Guangdong list page carries navigation only.
- Re-calibrated the corpus answer gate to `min_score 23.0 / min_matched 4` after the larger corpus shifted BM25 scores; the original anchors otherwise fell to 15/19.
- Gates: v1 dev 19/19, test 12/12, abstention 8/11, false refusals 2; v2 dev correctness 0.8776, citation 1.0000, recall 0.9625, abstention 0.9000. Acceptance: answer rate 0.4590, point coverage 0.1766, citation accuracy 0.1706, misanswer 0.3286 (+1.43 pp against the 0.3143 baseline, inside the 2 pp tolerance).
- Indexes: v1 `686bc13a5ddc` with 1,661 chunks; v2 `59c70969e461` with 48 documents and 1,486 chunks. Register is 91 sources (was 77).
- Tests: 445 passed, 2 skipped. No tag or release.

## 2026-11-07 — Answer contract v3

- Added `src/scs_fkb/answer_v3/`: three states (`answerable` / `partial` / `abstain`), conclusion-first assembly with conditions, an as-of declaration, numeric anchors with basis, out-of-scope detection and gap-to-channel mapping (`configs/answer-channels.yaml`).
- Responses now carry `answerability`, `conclusion`, `conditions`, `gap`, `channel`, `as_of` and `numbers`; `SCS_FKB_ANSWER_CONTRACT=v1` restores the old text for reproduction.
- Acceptance (512, extractive): misanswer 0.3286 → 0.2571, refusal-with-channel 0.0286 → 0.5857, as-of declaration 0.0877 → 0.3509; point coverage 0.1766 → 0.1753 and citation 0.1706 → 0.1714 stay flat. v1 gate 19/19 + 12/12 + 8/11; v2 gate dev correctness 0.8776 → 0.8867, citation 1.0, recall 0.9625, abstention 0.90.
- 10 contract unit tests plus two service tests; total 457 passed, 2 skipped. No tag or release.

## 2026-11-07 — Acceptance scoring calibrated

- Calibrated the acceptance scorer without touching corpus, retrieval, answers or questions: topic-token citation matching with page/table labels, 23 typed element rules for points without literal anchors, and 113 grounded point overrides checked against the cited clause or the reference answer.
- Judgeable required points rose from 553/1,117 (49.5%) to **849/1,117 (76.0%)**; 268 points remain semantic (negations, case judgements).
- Re-baselined 512: point coverage 0.1753 → **0.1684**, citation accuracy 0.1714 → **0.3810** (denominator grew and the newly judged points are mostly missed); misanswer 0.2571, refusal-with-channel 0.5857, as-of 0.3509 and basis 0.0263 unchanged.
- Published the failure backlog: 171 questions still reference missing documents, 130 citation locations unmatched, 125 answered with zero coverage, 88 wrong documents, 37 missing as-of declarations, 18 refusal-test misanswers.
- 23 scorer tests; full suite green. Private report and backlog under the run root; no tag or release.


## 2026-11-07 — Corpus batch 2: eight documents registered, indexing deferred

- Attempted all 32 instruments the acceptance set still cites without a corpus document. Captured and registered eight with full provenance: the 2024 marine ecological bulletin, the sea-turtle and Indo-Pacific humpback dolphin action plans, the small-vessel statutory inspection rules, the wildlife-crime judicial interpretation (法释〔2022〕12号), the criminal-law text, the Guangxi vessel-upgrading policy explainer and the seawater-quality assessment regulation. Register 91 → 99 sources.
- Recorded 24 exclusions with reasons: no standalone public text (logbook, vessel-quota and minimum-size rules live inside already-indexed regulations), draft-only standards (hypoxia, heatwave, large-vessel inspection), policy-excluded marine-ranch material, and sources behind bot walls or dead links.
- Staging A/B measured a real conflict: indexing the batch under the current 19.0/3 answer gate raises refusal misanswer 0.2571 → 0.3714–0.4000 and lowers citation accuracy 0.3810 → 0.3487–0.3684. The index was restored to the 48-document baseline and the 512 run returned to 0.1684 / 0.3810 / 0.2571. Indexing is deferred to the answer-gate/retrieval task, which must re-run this A/B after aligning the gate.
- 83 config tests pass after the register-count sync; no tag or release.
