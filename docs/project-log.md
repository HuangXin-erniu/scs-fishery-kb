# Project Log

This log records material project changes by date. It does not use release versions and is not tied to GitHub Releases.

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
