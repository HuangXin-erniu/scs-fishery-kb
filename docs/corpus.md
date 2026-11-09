# Corpus Inventory

- Status: corpus and web layers registered and indexed for this phase. 99 sources (98 acquired, 0 open candidates), schema v4 currency, and 140 knowledge notes with 119 fetched cards; 48 public documents are indexed (1,486 chunks, index `59c70969e461`) and cards/notes live in a separate external store. The local core CSV has 3,126 rows and stays outside the public tree.
- Register: [configs/corpus.yaml](../configs/corpus.yaml)
- Candidate register: configs/candidates.yaml（已移除）（已移除）
- Indicator schema: configs/statistics.yaml（已移除）（已移除）
- Date: 2026-11-07

## 1. Purpose and scope

This inventory covers the knowledge layer: fishing-vessel operations and catch statistics, vessel/voyage data dictionaries, ocean and fishery product descriptions, fishery bulletins and historical records, laws and standards, and data dictionaries.

It does **not** include raw environmental grids, reanalysis data, forecast rasters or products, full AIS/VMS tracks, or unlicensed material. No data values are published in this repository.

## 2. Method

1. Define seven corpus types and register each source with title, publisher, year, type, format, location, licence, sensitivity, status, priority, volume, update frequency, hash and acquisition notes.
2. Hold every source whose licence or sensitivity is `unknown`.
3. Acquire only from official or owner-confirmed authoritative channels; record the retrieval path, date and SHA-256.
4. Keep source files in the local data root; the public register contains metadata, hashes and coverage counts only.
5. Parse and index the 28 public sources in the corpus store; cards and notes are built into a separate external store.

## 2a. Registry fields

Every entry carries schema v3 fields: `level` (national, provincial, municipal or international), `authority_tier` (A publisher page, B gazette or compilation, C municipal), `source_class` (normative, official_statistics, standard or reference), `license` and `sensitivity` (checked against the schema allowlist), `currency` (as-of date, basis, review date and review `cadence`), `retrieval` (channel and whether the text is parseable) and `lifecycle` (active or retired). Candidates are separate: a proposed page lives in `configs/candidates.yaml（已移除）` with an `open`/`accepted`/`rejected`/`expired` status and is never ingested or cited before acceptance. The field table and the admission, retirement and deletion rules are in [data-model.md](data-model.md); `src/scs_fkb/registry.py` and `src/scs_fkb/candidates.py` enforce them, and `scs-fkb sources check` gates CI.

## 3. Types

| Type | Name (zh) | Sources | Description |
|---|---|---:|---|
| `statistical_yearbook` | 统计年鉴 | 10 | Official annual statistics and indicator tables |
| `operations` | 作业知识 | 1 | Fishing methods, gear, vessel operations, logbooks and permit conditions |
| `law` | 法律 | 1 | National law adopted by the legislature |
| `regulation` | 行政法规/规章/地方性法规 | 20 | Administrative regulations, departmental rules and local regulations |
| `notice` | 通告/公告 | 12 | Official notices, announcements and seasonal measures |
| `standard` | 标准/规范 | 17 | National, industry or provincial standards and operational norms |
| `fishery_product` | 渔情/海况产品说明 | 0 | Product descriptions, fishery bulletins and historical records |
| `data_dictionary` | 数据字典 | 2 | Field definitions, indicator definitions, metadata and quality rules |
| `plan` | 规划/方案 | 0 | Official plans, programmes and construction layouts |

## 4. Acquired yearbooks

The first eight editions are owner-confirmed official/authorized Excel editions; the ninth is an image-only scan. The public metadata records edition, data year, file count and manifest SHA-256; values stay local.

| Source | Edition | Data year | Files | Format | Manifest SHA-256 (short) |
|---|---:|---:|---:|---|---|
| `STAT-YB-2018` | 2018 | 2017 | 86 | xlsx | `9b5ddea6` |
| `STAT-YB-2019` | 2019 | 2018 | 137 | xls | `025f4a43` |
| `STAT-YB-2020` | 2020 | 2019 | 140 | xls | `71d5033b` |
| `STAT-YB-2021` | 2021 | 2020 | 84 | xlsx | `edd634e9` |
| `STAT-YB-2022` | 2022 | 2021 | 84 | xlsx | `4d6f56e8` |
| `STAT-YB-2023` | 2023 | 2022 | 84 | xlsx | `e8cb6104` |
| `STAT-YB-2024` | 2024 | 2023 | 140 | xls | `dc4c7475` |
| `STAT-YB-2025` | 2025 | 2024 | 82 | xlsx | `8768019d` |
| `STAT-YB-2026` | 2026 | 2025 | 1 | pdf | `ef674e53` |

The 2026 edition is a 166-page scan with no text layer. Its contents were mapped to a table list covering seven parts and the appendices, and six tables were transcribed for the national total plus Guangdong, Guangxi and Hainan (140 non-empty cells): output, capture by sea area, capture by gear, capture vessels by operation type, fishing ports and fishery population. Values stay in the local run root. The remaining tables, including the species breakdown, are not extracted yet. OCR or manual entry is the prerequisite. The 2022 bundle contained a byte-identical duplicate of table 3-10; the duplicate was removed on 2026-10-31 and that edition's manifest regenerated, so its hash is the SHA-256 of the regenerated manifest. The 2024 edition is encrypted with the Excel default password; the originals are unchanged in `raw/STAT-YB-2024/`, and decrypted working copies are kept outside the public tree. The 2019, 2020 and 2024 editions use the older `.xls` layout.

The six national fishery-economy bulletins were removed on 2026-11-02: they report total output including culture, and the corpus keeps only statistics that carry a capture series. The capture record now comes from the nine yearbook editions and the China Statistical Yearbook chapter 12.

`STAT-CSY-027` is the China Statistical Yearbook 2026 Excel set (1,318 files, Chinese and English editions, internal). Its chapter 12 covers agriculture; table 12-15 gives a national aquatic-production series and provincial 2025 totals with marine capture and aquaculture splits. The Excel set does not include the printed indicator explanations, so it is not a definition source.

## 5. Acquired policy documents

| Source | Type | Jurisdiction | Document | Status |
|---|---|---|---|---|
| `POL-LAW-009` | `law` | national | Fisheries Law, 2025 revision | acquired; text of the official People's Daily publication, 2026-02-25 (主席令第六十三号) |
| `POL-RULE-018` | `regulation` | national | Implementing rules for the Fisheries Law, 2020 revision | acquired |
| `POL-RULE-019` | `regulation` | national | Regulation on fishing-vessel inspection, 2003 | acquired |
| `POL-RULE-020` | `regulation` | national | Measures for levying and using the fishery resource proliferation fee, 2011 revision | acquired |
| `POL-STD-010` | `regulation` | national | Fishing permit regulation, 2022 revision | acquired |
| `POL-CREW-055` | `regulation` | national | Measures for the administration of fishery crew members, 2022 revision | acquired; 2022-01-07 republication, 54 articles and four annexes |
| `POL-CLOS-015` | `notice` | national | Seasonal closure notice, 2023 | acquired |
| `POL-GD-021` | `regulation` | guangdong | Guangdong fishery management regulations, 2019 amendment | acquired |
| `POL-GD-022` | `regulation` | guangdong | Guangdong fishing-port and fishing-vessel regulations, 2020 amendment | acquired |
| `POL-GX-023` | `regulation` | guangxi | Guangxi measures implementing the Fisheries Law, 2016 amendment | acquired |
| `POL-GX-024` | `regulation` | guangxi | Guangxi fishing-port and fishing-vessel regulations, 2024 amendment | acquired |
| `POL-FJ-025` | `regulation` | fujian | Fujian measures implementing the Fisheries Law, 2019 amendment | acquired |
| `POL-FJ-026` | `regulation` | fujian | Fujian fishing-port and fishing-vessel regulations, 2010 amendment | acquired |
| `POL-GEAR-016` | `notice` | national | Minimum-mesh system for permitted and transitional gear, 2013 | acquired; in force 2014-06-01, annexes registered separately |
| `POL-SPEC-041` | `notice` | national | Closed-season special-permit arrangement for 2026 | acquired; permits Sthenoteuthis oualaniensis in the South China Sea for Guangxi and Hainan |

The legal corpus now covers the national law, its implementing rules, vessel inspection, the resource levy, the fishing-permit rules, the seasonal closure and the 2026 special-permit arrangement, plus the Guangdong, Guangxi and Fujian regulations. Each document records its publisher, revision history, article count and SHA-256. Article counts: Fisheries Law 90, implementing rules 42, vessel inspection 40, levy measures 18, permit regulation 59, closure notice 4 sections, special-permit notice 3 annexes, Guangdong fishery 47, Guangdong port and vessel 44, Guangxi implementation 48, Guangxi port and vessel 37, Fujian implementation 61, Fujian port and vessel 46. The 2026 notice is registered from the ministry's OFD attachment, a 22-page XML container whose text layer extracts without OCR; it allows Sthenoteuthis oualaniensis permits in the South China Sea north of 12°N (36 Guangxi vessels and 2,500 t from 20 June to 5 August; 70 Hainan vessels and 5,000 t from 1 May to 15 August; mask net 35 mm) and adds 26 Hainan auxiliary vessels. Its operation-type permits cover only the Yellow and East China Seas.

The Fisheries Law text is the owner-supplied DOCX of the official 人民日报 publication. The article openings were cross-checked against the electronic edition before the duplicate copies were removed on 2026-10-31; the registered DOCX is now the single retained text. The official ministry PDF edition of the fishing-permit regulation (29 pages) is kept beside the registered HTML as a format copy; its articles 50–53 carry the logbook obligation.

## 5a. Acquired standards and operations supplements

| Source | Type | Document | What it answers |
|---|---|---|---|
| `POL-GEAR-033` | `standard` | Minimum mesh sizes for permitted marine capture gear | Gear classes and minimum mesh by sea area and target species |
| `POL-GEAR-034` | `standard` | Minimum mesh sizes for transitional gear | Trawl, gillnet, purse seine, stow-net, cage and trap classes |
| `OPS-STD-035` | `standard` | SC/T 9460—2025 marine capture information sampling survey | Defines marine capture information and sample vessels; sets monthly collection and quality control; cites GB/T 5147—2003 for gear classification |
| `OPS-STD-039` | `standard` | GB/T 5147—2026 fishing-gear classification, naming and codes | The national classification that maps yearbook gear groups and permit operation types |

The mesh tables are annexes 1 and 2 of the 2013 notice `POL-GEAR-016`, which entered into force on 2014-06-01 and repealed the 2003 notice. SC/T 9460—2025 was published 2025-12-09 and takes effect 2026-05-01; GB/T 5147—2026 was published 2026-02-27 and takes effect 2026-09-01, replacing the 2003 edition. The SC/T series entry was removed on 2026-11-03 together with the permit-form instruction; the seventeen image-only reference copies remain catalogued in `configs/sc-standards.yaml（已移除）`. The seven in-scope standards without a public text were excluded from the project on 2026-11-01. SC/T 9460—2025 stays registered as `OPS-STD-035`; aquaculture, feed, disease, processing, hull-construction, ship-equipment and freshwater-survey series are out of scope.

## 5b. Acquired definitions

| Source | Publisher | What it defines |
|---|---|---|
| `DICT-STAT-013` | 农业农村部渔业渔政管理局 | Appendix 3 of the 2024 fisheries yearbook: the water-product concept and scope, the reporting unit, the fresh-weight basis, the culture-versus-capture rule, product classes, and capture production by sea area (with the Bohai, Yellow, East China and South China Sea boundaries) and by gear group |
| `DICT-STAT-040` | 国家统计局 | Chapter-12 notes of the 2025 national yearbook: the national definition of water-product output as the final effective output of capture and culture, reported through fishery departments, fresh weight since 1996; no sea-area or gear split |

The two agree on the concept and differ in scope: the national note sets the headline indicator, while the fisheries appendix supplies the operational rules the sea-area and gear tables depend on.

## 5c. International reference

| Source | Publisher | What it provides | Index status |
|---|---|---|---|
| `STD-CWP-043` | FAO Coordinating Working Party on Fishery Statistics | The CWP Handbook pages that define catch, landings and fishing effort, list the standard effort measures (A1-C6) and publish the ISSCFG gear classification | Not indexed: English text, and a dry run lowered abstention from 5/6 to 4/6 without improving Chinese-question recall |

CWP carries the FAO open-access licence CC BY-NC-SA 3.0 IGO, so it stays local and nothing is copied into this repository. A project-authored terminology bridge in [configs/glossary-bridge.yaml](../configs/glossary-bridge.yaml) maps five Chinese statistical terms to the CWP concepts and feeds the reference channel, so a Chinese definition question can reach the English pages without joining the main index. CWP is the international counterpart of definitions the domestic yearbooks leave implicit: `DICT-STAT-013` and `DICT-STAT-040` define production, while landed weight and fishing effort only have the CWP definitions. A Chinese official definition is still missing. Per-page hashes live in configs/cwp-handbook.yaml（已移除）（已移除）. The five remote product documents (MUR, OLCI, GFW, CMEMS, HY-1C/D) and the ASFIS code list were removed on 2026-11-03; the web layer replaces them with cached cards, and the two product questions Q-E08 and Q-M09 are parked until that layer lands.

## 5d. Statistical governance and monitoring

| Source | Publisher | Status on 2026-11-02 | What it provides |
|---|---|---|---|
| `POL-STAT-050` | 农业农村部（原农业部） | Current; no repeal found (农渔发〔2010〕5号) | Duties, submission and quality rules for fishery statistics: the process behind the yearbook |
| `POL-STAT-051` | 国家统计局 / 农业农村部 | Current; 国统制〔2024〕120号, valid to June 2027 | The 2024 fishery statistics survey system, replacing the 2021 approval that expired in February 2024 |
| `POL-VMS-053` | 农业农村部 | Current; repealed the 2014 measures | Distant-water vessel position monitoring duties, not near-shore VMS fields |
| `STD-ECERT-054` | 农业农村部办公厅 | Current (2025) | Electronic certificate standards C 0402—2024, C 0403—2024 and C 0374—2024 for quota approval, ownership registration and nationality |

All four remaining entries are indexed in the policy reference collection. The 2021 survey system has expired, so `POL-STAT-051` registers the 2024 text with its new approval number. Both annual monitoring circulars were removed on 2026-11-03 as historical work records. The 2024 monitoring letter (农渔科函〔2025〕87号) is quoted by provincial sites but not published in full; the ministry gazette index exposes no file list and the national marine forecast portal is a single-page service without a downloadable product document, so Q-M07 stays uncovered. Near-shore VMS definitions and a data-sharing metadata rule remain uncovered, and Q-M02, Q-M06 and Q-M11 stay out of reach.

## 5e. Crew management

| Source | Publisher | Currency | What it provides |
|---|---|---|---|
| `POL-CREW-055` | 农业农村部 | Current; the 2014 order was amended in 2017 and 2022, registered from the 2022-01-07 republication | Certificate grades, the minimum manning table, the captain duty to fill the fishing log and the penalty range for crew and owner breaches |

The crew rule turns the crew line from a provincial principle into a national rule: the Guangdong, Guangxi and Fujian port-and-vessel regulations state crew and safety duties in general terms, while `POL-CREW-055` carries the manning table and the certificate grades.

The crew rule is routed through the policy collection, which already passes the raw Chinese question.

Hainan remains the open jurisdiction: the provincial government page carries the 2008 amendment and is marked 已修改, and the national law database confirms the 2013 revision is in force but serves the body only through a script-driven page and a signed attachment this network cannot extract. No superseded text is registered, so the Hainan gap stays open with its evidence rather than being filled with a stale copy.

The terminology bridge stays for the CWP channel. The product channel and its four ocean-colour terms (水色, 覆盖周期, 重访, 幅宽) were retired with the product documents on 2026-11-03; the four abstention tests are unchanged. The bridge remains a retrieval mapping, not a translation, and each entry says so in its note.

## 5f. Jurisdiction documents for the 2026 closure

| Source | Level | Currency | What it provides |
|---|---|---|---|
| `POL-HN-058` | provincial (Hainan) | In force; 2013 revision, published 2013-12-03, effective 2014-01-01 | The Hainan implementing measures: capture permits, closed areas and seasons, protected areas and legal liability |
| `POL-HN-059` | provincial (Hainan) | Current for 2026; published 2026-04-24 | The Hainan closure notice: dates, the 26°30′N to 12°N area, vessel classes, port and gear rules, the 2026-law penalty ladder and the subsidy deduction |
| `POL-GX-060` | provincial (Guangxi) | Current for 2026; published 2026-04-22 | The Guangxi closure notice: the same dates and the 12°N boundary, port-of-registry berthing, special permits, the subsidy deduction and the 15-day departure ban |
| `POL-GD-061` | municipal (Shantou) | Current for 2026; published 2026-04-28 | The Shantou notice: the Guangdong area boundary (12°N to the Fujian-Guangdong line), the dates, the closure classes, 船进港、人上岸、网入库 and the 2000000 yuan ceiling |

The audit gap closes here: Hainan had no document at all while Guangdong, Guangxi and Fujian carried two regulations each. The Hainan entry is the in-force 2013 revision; the earlier 2008 page on the same portal is marked 已修改 and is deliberately not registered. Guangdong is the one honest asymmetry: the provincial 2026 work plan (粤农农函〔2026〕208号) is cited by municipal notices but is not published on the provincial site, so the register holds the Shantou municipal implementation and its notes say so rather than presenting it as the provincial text.

Every policy document now carries a jurisdiction code and a level (national, provincial or municipal). The lookup sorts stably: a named province first, then the national layer, then other provinces and the municipal layer; with no province named it puts national before provincial before municipal. The composed answer leads with the province sentence when a province is named. Because the closure words are cues again, the national closure question now has a policy block that leads with the 2026 enforcement notice instead of an empty block; that is the intended consequence of ranking the national basis first, and it replaces the earlier behaviour where the block stayed empty. The reference blocks also deduplicate passages and cap a single document at two passages, so a short document cannot crowd out its neighbours.

## 5g. Standard hull types and the catalog block

| Source | Level | What it provides |
|---|---|---|
| `STD-HULL-062` | ministerial (annex to 农办渔〔2017〕5号) | The three-level hull-type evaluation (形式审查, 量化评分, 专家评分), the naming method and the application forms for marine capture vessels over 12 m |

The task was to register a hull-parameter catalog. The three near-shore provinces publish none in a form this pipeline can read. Guangdong announces 83 hull types in the 2020 second batch and 4 in 2021 on dara.gd.gov.cn, but the parameters are xlsx attachments and the pages are mostly navigation. Hainan announces 7 large and 15 small types in its 2019 notice, but the notice PDF is an image-only scan and the two catalogs are xls attachments. Guangxi has no public catalog found. The extraction pipeline has no xlsx parser, so registering a catalog would create the very defect the audit found: a document in the register that no question can reach. The evaluation method is parseable, upstream of all three catalogs and cited by the Hainan announcement, so it is registered instead. Hull-parameter questions stay uncovered until the project adds an xlsx or table channel, and that is a separate decision rather than an assumption.

## 5h. Fujian standard hull catalogs and the two open gaps

| Source | Scope | What it provides |
|---|---|---|
| `POL-FJ-063` | provincial (Fujian), 闽海渔〔2025〕4号 | The notice that publishes the sixth and seventh batches; cites 农办渔〔2017〕5号 and marks itself 有效 |
| `STD-FJ-064` | province-wide | The sixth-batch catalog: 船型名称, 总长, 船长, 型宽, 型深, 主机功率, 总吨位 and 版权单位 |
| `STD-FJ-065` | province-wide | The seventh-batch catalog with the same parameter set plus 图纸名称, for example the 31.7 m GRP jigging vessel at 26.70 m length, 6.20 m beam, 202 kW and 132 GT |
| `STD-FJ-066` | Pingtan pilot zone only | One 33.6 m steel jigging type; the scope limit must travel with any answer drawn from it |

The hull-parameter gap closes here, and only here: the three catalogs are docx, the parser dispatch added in the previous task reads them, and the parameter tables come out as text. They cover Fujian hull types and nothing else. Guangdong still publishes its catalogs as xlsx attachments and Hainan as an image-only scan, so the Guangdong and Hainan parameter questions stay uncovered and the register does not pretend otherwise.

Two gaps were re-checked in the same task and stay open. The 2024 monitoring letter (农渔科函〔2025〕87号) still has no public full text: the ministry gazette issue pages are script shells without a file list and provincial sites only quote the letter. The Guangdong 2026 work plan (粤农农函〔2026〕208号) is not on the provincial agriculture site or the provincial gazette; the municipal notices of Shantou, Yangjiang, Zhongshan, Wuchuan and Zhanjiang cite it but none carries the provincial text as an attachment, so `POL-GD-061` remains the registered evidence and is labelled municipal.

## 5i. Spreadsheet catalogs and the table channel

| Source | Province | Sheet contents |
|---|---|---|
| `STD-GD-064` | Guangdong | 2020 second batch, 83 hull types with 总长, 公约船长, 型宽, 型深, 总功率, 总吨位, evaluation scores and the design unit |
| `STD-GD-065` | Guangdong | 2021 batch, four hull types with the same parameter set |
| `STD-HN-066` | Hainan | 2019 small-vessel catalog (附件2 on the page, but the figure on disk is the one named 小型 in its own header) |
| `STD-HN-067` | Hainan | 2019 large and medium-vessel catalog (附件1), header sheet plus a data sheet |

The pipeline now reads `.xlsx` with openpyxl and `.xls` with xlrd: one page per worksheet, the sheet name as the first line and each row joined by ` | `. Values are printed as published and never converted, so a citation shows the row itself. The reference loader already dispatches on the suffix, so the catalogs are reachable as soon as they are registered.

One trap is worth recording: the Hainan page lists 附件1 (large and medium) after 附件2 (small), and the file names carry no hint, so the two downloads were opened and their sheet headers checked before registration; the ids follow the sheet content, not the link order. Guangdong has no announced later batch that this network can reach, so the two batches registered here are the latest public ones and the source-watch list keeps the announcement page under observation.

## 5j. Live watch run and the two open gaps

The first live watch run reported nine of ten sources unreachable. That was a false negative, not a dead page: this network intercepts TLS and the project venv trust store lacks the interception root, so urllib raised a certificate-verification error while curl, reading the system keychain, succeeded. The checker now honours `SCS_FKB_CA_BUNDLE`, falls back once to `/etc/ssl/cert.pem` on a certificate error and never disables verification; with that change all ten seeded sources answer 200 and are recorded as unbaselined.

The gap review was repeated against the live pages and both gaps stay open. The national station column (nftec.agri.cn/yqxx/) lists 2021–2026 news items, including a 2025 statistics workshop, but carries no full text of the 2024 monitoring letter. The Guangdong notice and policy lists answer 200 but neither shows the 2026 closure work plan (粤农农函〔2026〕208号) on its first page. The ministry gazette 2025 index answers with a small page that carries no file list, so the letter cannot be confirmed from there either. Nothing new is registered for either gap.

The NSOAS *China Ocean Satellite Application Report 2021* is not registered. It states that 368 issues of near-real-time fishery and sea-state analysis and forecast information were released to national distant-water fishery enterprises in 2021, which is the best public evidence for the publication cadence behind Q-M07. The file, however, is 178 MB for 39 pages and would more than double the local data root, so the owner decides whether to accept that weight; it is not registered unilaterally.

## 5k. National closure basis and the reference layer

| Source | Level | Status | What it does |
|---|---|---|---|
| `POL-LAW-009` | national law | in force since 2026-05-01 | The legal basis the 2026 closure notices cite |
| `POL-CLOS-015` | national notice | in force | The 2023 adjustment (农业农村部通告〔2023〕1号), the system basis; the 2026 Hainan and Guangxi notices cite it |
| `POL-SPEC-041` | national notice | in force for 2026 | The 2026 special-permit and auxiliary-vessel arrangement |
| `POL-ENF-068` | national notice | in force for 2026 | The 2026-04-29 three-ministry enforcement deployment, 1 May to 16 September |
| `POL-STD-010`, `POL-RULE-018` | national regulations | in force | The 2022 permit regulation and the 2020 implementing rules; both predate the 2025 law and are watched for alignment |

The provincial and municipal closure notices (`POL-HN-058`, `POL-HN-059`, `POL-GX-060`, `POL-GD-061`) stay registered as references. They do not define the system and they are not promoted to the national basis; a question about the institution is answered from the national notices, while a question that names a province can still use that province's notice.

The chain is recorded rather than assumed: every entry above carries a currency block with an as-of date, a basis and a review date. Nothing is marked superseded without a named successor, and a text that was replaced before registration (the 2021 closure notice, the 2021 distant-water hull series) is named in the note but not registered as a source.

## 5l. National hull-standard package and the 2018 record that stays open

| Source | Level | Status | What it is |
|---|---|---|---|
| `STD-HULL-069` | national notice (农办渔〔2017〕5号) | in force | The promulgating notice for the evaluation method, with two annexes |
| `STD-HULL-062` | national method (annex 1) | in force | The three-level evaluation and the naming rules |
| `STD-HULL-070` | national usage notes (annex 2) | in force | The coefficients and scoring inputs behind the method |
| `STD-YY-071` | national parameter series (农办渔〔2024〕15号) | in force since 2024-12-01 | The distant-water standard-hull parameter table, ten pages |
| `SC/T 8003-2007` | national standard | in force | The hull-type classification and numbering code; no dimensions |

The national layer now states what the method is and how it is applied, and it carries one national parameter table. The scope boundary is recorded in the entry itself: the 2024 series covers ocean-going hull types, so it is not evidence for a near-shore parameter question, and the provincial catalogs (Fujian, Guangdong, Hainan) remain the near-shore reference layer. The earlier 2021 edition of the series is named as the superseded predecessor but is not registered.

The 2018 distant-water parameter series was published in 农业农村部公报 2018 年第 11 期 and is named in `STD-YY-071` as the predecessor of the 2021 and 2024 editions; it is not registered because the 2024 edition is current.

One national record stays open: the 2018 quarterly evaluation results (66 hull types, including Guangxi) would list provincial types, but only news restatements were found and no publisher page could be reached. It is recorded as unattainable rather than reconstructed, and SC/T 8003-2007 is explicitly noted as a code standard that cannot substitute for a parameter catalog.



### 2018 search record

The 2018 first-quarter evaluation results were pursued with four query phrasings, the ministry search endpoint and the bureau search path (both HTTP 404), the 2018 gazette issue pages 201804 to 201812 (about 85 KB each, script shells with zero occurrences of 标准船型), and the archive.org CDX interface (connection timed out from this network). The only reachable traces are news restatements on research-institute pages, which are pointers and not sources. The 66-type list therefore stays unattainable and is not reconstructed; the bureau notice list is in the watch list so a future upload is detected.


### 广西 hull-catalog search record

Guangxi is the one coastal province without a public marine hull catalog. The provincial notice and document lists (https://nynct.gxzf.gov.cn/xxgk/jcxxgk/tzgg/ and /wjzl/) answer 200 but are script shells with zero 船型 occurrences; the former ocean bureau domain http://www.gxao.org.cn/gxhyj_bumenwenjian returns 404; the Qinzhou approval that cited the catalog (http://nynct.gxzf.gov.cn/xwdt/gxlb/qz/t11054826.shtml) also returns 404. The only reachable material is the 2020 inland pontoon standard (桂农厅办发〔2020〕47号), which is inland and out of scope, and municipal approvals that reference the catalog without carrying it. The catalog therefore cannot be registered from public pages today. The owner has a ready-to-submit disclosure request in [foi-guangxi-hull-catalog.md](foi-guangxi-hull-catalog.md); both department lists are in the watch list so a future upload is detected.

## 5m. Environment, climate and marine hazards

| Source | Level | Current | Retrieval | What it provides |
|---|---|---|---|---|
| `POL-OBS-072` | national regulation | in force (2023-07-20 revision) | collection | The Ocean Observation and Forecasting Regulation: observation networks, forecasting duties and marine hazard warning responsibilities |
| `STAT-ECO-073` | national bulletin | latest edition (2026-06-08) | collection | The 2025 marine ecological early-warning monitoring bulletin, 76 pages on ecological status, pressures and early warning |
| `STAT-DIS-074` | national bulletin | latest edition (2024-04-22) | none (provenance) | The 2023 marine disaster bulletin: storm surges, waves, sea ice, tsunami, green tide and red tide, with loss statistics |

The disaster bulletin is registered with `parseable: false` and `retrieval.channel: none`: its embedded fonts map to garbled glyphs, so the text layer cannot be cited. It stays as provenance with channel none, not as an answer source or a collection document.

Rejected after checking: the 2026 marine disaster emergency plan (自然资办函〔2026〕1023号) renders its body by script on both the ministry and gov.cn pages, and the 2022 version it repeals is likewise unreadable, so neither is registered; the GB/T 19201-2006 cyclone-grades PDF is image-only; the national forecast centre site is a script shell. Typhoon grading therefore stays uncovered until a text-bearing official copy is available.

## 5n. Species and resource conservation

| Source | Level | Current | Retrieval | What it provides |
|---|---|---|---|---|
| `POL-RES-075` | national regulation | in force | collection | The 2009 aquatic stocking regulation: planning, species choice, quarantine, supervision and evaluation of stock enhancement |
| `STD-SPEC-076` | national announcement | in force (2021-02-05) | none (provenance) | The 2021 national key-protected wildlife list (980 species and 8 groups); the PDF is image-only, so it is provenance only and cannot answer a species-level question |

One limit is recorded rather than hidden: the germplasm-reserve download from the Chinese Academy of Fishery Sciences returned the 2013 fishery eco-environment bulletin instead of the reserve list, which is not registered. Species identity and distribution will come from cached WoRMS and FishBase cards in the web layer.

## 5o. Ports, anchorages and operations

| Source | Level | Current | Retrieval | What it provides |
|---|---|---|---|---|
| `POL-PORT-077` | national regulation | in force (2019-03-02 amendment) | collection | The fishing-port traffic safety regulation: navigation, berthing, safety and supervision in port waters |
| `POL-PORT-078` | national announcement | current 2025 first batch | collection | The 2025 port-grade recognition list: twelve central ports and the first-class ports |

Shelter anchorages stay uncovered: no national public list was found, only foreign regulations and provincial documents that reference lists without publishing them. The twelve operation types are already covered by `POL-STD-010` and the gear standards, so no duplicate source was registered for them.

## 5p. Enforcement and currency evidence

| Source | Level | Current | Retrieval | What it provides |
|---|---|---|---|---|
| `POL-PEN-078` | national regulation | in force (2025-07-15 revision) | collection | The fishing-port and navigation penalty rules: grounds and ranges for port-traffic and fisheries violations |
| `POL-LIST-079` | national announcement | current (2025-09-24) | collection | The ministry catalogue of rules in force, used as the citation for in-force status |

The catalogue is the evidence rather than an inference: it lists the fisheries crew measures and the fishing-permit regulation, so `POL-CREW-055` moved from unknown to in force with the announcement quoted, and `POL-STD-010` carries the same cross-check. It does not list the fishing-vessel inspection rules, which sit with the transport ministry, so that regulation is not registered here.

## 5q. Source classes and review dates

The register no longer carries an in-force / not-applicable / unknown status. Each entry states what kind of source it is and when it must be checked again:

| Field | Values | Meaning |
|---|---|---|
| `source_class` | `normative` (33), `official_statistics` (10), `standard` (18), `reference` (8) | What the entry is, not whether it is current |
| `currency.as_of` | date | When the entry was last checked |
| `currency.basis` | publication / edition / announcement / retrieval | What the check rested on |
| `currency.review_due` | date | When it must be reviewed; normative 30 days, standard 90 days, official_statistics one annual edition, reference 180 days |
| `currency.note` | optional | The evidence sentence (commencement clause, approval number, publication date) or a review remark |

The 2026-11-03 migration replaced the old statuses without losing evidence: the substantive sentences moved into `currency.note`, the category notes were dropped because `source_class` now carries that information, and every entry keeps a review date. The watch report lists entries whose `review_due` has passed; it never changes an answer by itself.

## 5r. Climate and hazard: documented unavailability

Four official routes were checked and none yields citable text today. They are recorded rather than replaced:

| Route | Evidence | Consequence |
|---|---|---|
| 气象灾害预警信号发布与传播办法 (中国气象局令第16号) | The gov.cn text at https://www.gov.cn/zhengce/2007-06/12/content_5720083.htm parses 1,862 characters, but it is the 2007 order; a Jiangsu meteorological document states the current version is the March 2023 revision 气发〔2023〕34号 | The 2007 text is not registered; a 2023 text page was not found, so the watch monitors the CMA rules page |
| GB/T 19201-2006 热带气旋等级 | The cma.gov.cn PDF (234,082 bytes) is image-only and parses no text | Not registered; a text-bearing copy would be needed |
| GB/T 19721.1/.2/.3-2017 storm-surge and wave warning standards | No public text copy exists; the standard platform exposes metadata only | Not registered; covered by the same unavailability record |
| 2026 marine disaster emergency plan (自然资办函〔2026〕1023号) | Both gi.mnr.gov.cn and gov.cn render the body by script; the 2022 predecessor is likewise unreadable | Not registered; the ministry page is watched for a text upload |

The domain therefore stays uncovered on purpose: no typhoon grade, storm-surge or wave-warning text is cited, and no answer should imply one. `WATCH-CMA-RULES` and `WATCH-MNR-EMERGENCY` carry the monitoring.

## 5s. Scope boundary: capture, not aquaculture

The knowledge base covers nearshore South China Sea capture, fishing-vessel operations and fishery-condition material. Aquaculture, artificial breeding, marine-ranching production and processing are out of scope and are not registered.

Two entries were removed on 2026-11-02 under this rule: `POL-BREED-084` (人工繁育国家重点保护水生野生动物名录) and `POL-RANCH-083` (国家级海洋牧场示范区名单), together with their collection entries, watch entries, pipeline reference and local files. Both describe breeding or ranching support rather than capture.

In scope and kept: `POL-WATCH-082` (渔业船舶航行值班准则, vessel operations) and `POL-RES-075` (水生生物增殖放流管理规定, releases that restore capture stocks — a fishery-resource instrument, not a farming standard). Purely inland and freshwater material is also out of scope.

## 5t. Scope audit of the register

Every active entry was scanned on its title and notes for 养殖, 繁育, 海洋牧场, 加工, 饲料, 病害, 淡水, 内陆, 内河 and their English equivalents. No further pure aquaculture, breeding, ranching, processing or inland entry remains. The borderline entries are kept with a stated reason rather than left ambiguous:

| Entry | Why it stays |
|---|---|
| `POL-RULE-020` 渔业资源增殖保护费征收使用办法 | Charges capture, not farming; a resource-management instrument |
| `POL-RES-075` 水生生物增殖放流管理规定 | Governs releases that restore capture stocks; a fishery-resource instrument |
| `DICT-STAT-013`, `DICT-STAT-040` | Indicator definitions needed to read the statistics; they define capture and culture output separately |
| `STAT-CSY-027` | The statistical yearbook chapter used by the statistics channel |
| `STD-SPEC-076` | National protected-species list, kept as provenance for bycatch and protection reference; image-only |

The rule is enforced by a test: a new active entry whose title contains an out-of-scope term fails unless its id is explicitly allowlisted.

## 5u. Web cards

Eight cached cards extend the corpus beyond its normative and statistical core. They are indexed beside it and cited with URL and fetch date.

| Card | Topic | Publisher | Fetched | SHA-256 (short) | What it provides |
|---|---|---|---|---|---|
| `WEB-WORMS-LARIMICHTHYS-CROCEA` | species | WoRMS | 2026-11-03 | `0949f07c12fb` | Aphia taxonomy record for 大黄鱼 |
| `WEB-WORMS-TRICHIURUS-LEPTURUS` | species | WoRMS | 2026-11-03 | `d32d0821a39c` | Aphia taxonomy record for 带鱼 |
| `WEB-WORMS-DECAPTERUS-MARUADSI` | species | WoRMS | 2026-11-03 | `52d13dc407c0` | Aphia taxonomy record for 蓝圆鲹 |
| `WEB-WORMS-FENNEROPENAEUS-CHINENSIS` | species | WoRMS | 2026-11-03 | `bd073fad1978` | Aphia taxonomy record for 中国明对虾 |
| `WEB-FAO-ISSCFG-GEAR` | gear | FAO | 2026-11-03 | `516e1eebaa5e` | ISSCFG fishing-gear categories and definitions |
| `WEB-GOV-CMA-WARNING-2007` | hazard | 中国政府网 | 2026-11-03 | `8280090b25aa` | 气象灾害预警信号发布与传播办法: typhoon and gale signal levels |
| `WEB-NASA-OCEANCOLOR` | environment | NASA | 2026-11-03 | `2710de58e23a` | Ocean Biology DAAC ocean-colour product description |
| `WEB-EUMETSAT-SENTINEL3` | environment | EUMETSAT | 2026-11-03 | `0a1e77b05433` | Sentinel-3 mission and OLCI instrument description |

Two attempts failed and are recorded rather than replaced with weaker sources: the Copernicus catalogue PUM PDF reset the TLS connection, and the PO.DAAC MUR product page timed out. Cards are fetched only by `scs-fkb web refresh`; the text lives under the private data root and the public register keeps URL, publisher, fetch time, hash and a 300-character excerpt. The layer is deliberately small: it covers what the corpus cannot state (species identity, international gear classes), and the review date is 30 days.

## 6. Candidate sources

None. The three vessel/voyage and metadata candidates were removed on 2026-11-03 as unacquired and outside the current phase. Papers and reports were removed from the register because they are not accepted as authoritative project sources at this stage.

## 7. Status summary

| Metric | Value |
|---|---:|
| Corpus types | 7 |
| Registered sources | 63 |
| Acquired sources | 63 |
| Remaining candidates | 0 |
| Yearbook editions | 9 |
| Yearbook data years | 2017–2025 |
| Yearbook files | 838 |
| Local core CSV rows | 3,126 |
| Public values | 0 |
| Local 2025 sample rows | 140 |

## 8. Core coverage

The coverage matrix uses the latest edition for each data year. Counts are table counts, not values. The 2025 row reflects the six-table sample, not a complete extraction.

| Data year | Capture (sea/gear/species) | Vessels (type/power/length) | Population | Marine capture value | Coastal ports |
|---|---|---|---|---|---|
| 2017 | 1 / 1 / 1 | 1 / 1 / 1 | 1 | 2 | 1 |
| 2018 | 1 / 1 / 6 | 2 / 1 / 1 | 2 | 5 | **missing** |
| 2019 | 1 / 1 / 6 | 2 / 1 / 1 | 2 | 5 | **missing** |
| 2020 | 1 / 1 / 1 | 1 / 1 / 1 | 1 | 2 | 1 |
| 2021 | 1 / 1 / 1 | 1 / 1 / 1 | 1 | 2 | 1 |
| 2022 | 1 / 1 / 1 | 1 / 1 / 1 | 1 | 2 | 1 |
| 2023 | 1 / 1 / 6 | 2 / 1 / 1 | 2 | 5 | 1 |
| 2024 | 1 / 1 / 1 | 1 / 1 / **missing** | 1 | 2 | 1 |
| 2025 (sample) | 1 / 1 / 0 | 1 / 0 / 0 | 1 | 0 | 1 |

Known gaps:

- Coastal-port infrastructure is missing from the yearbooks for data years 2018 and 2019: the 838-file inventory confirms that the 2019 and 2020 editions contain no infrastructure table. The port plan and the recognition proposal that could have supplied a baseline were removed on 2026-11-03, so the gap stays open rather than being filled from a non-comparable table.
- Data year 2025 is sampled, not complete: the six transcribed tables cover output, capture by sea area and gear, capture vessels by operation type, ports and population, while the species breakdown, power and length bands, value and the remaining tables are still to be extracted from the scan.
- The 2017 and 2021 source tables have only 沿海中心渔港 and 沿海一级渔港; the later tables add class 2, class 3 and unrated ports.
- The vessel-length proxy is missing for data year 2024; the 2025 edition dropped the marine vessel-length table and keeps only the all-vessel and inland tables. The gap is accepted rather than filled from a non-comparable table.
- The vessel-length table is a marine production-vessel proxy, not capture-only.
- The 2025 edition renumbers and reorganises the vessel tables, adding marine capture-vessel tables by power and operation type; compare editions by table title, not by table number.
- No registered edition publishes capture production by operation type; production is available by sea area, gear group and species only.
- The published South China Sea column includes Fujian in data years 2017–2020 and excludes it from 2021 onward. The CSV stores the published value, the Guangdong/Guangxi/Hainan subtotal and the difference.

## 8a. Sufficiency review

The 24 draft questions were checked against the registered sources on 2026-11-01: **10 are answerable, 6 partially answerable and 8 not answerable**. Every unanswerable question maps to material outside the registration scope (vessel/voyage dictionaries and the excluded environment and fishery-product sources); nothing in the P1 scope is blocked. The draft has since been edited: Q-E08 and Q-M09 moved to the parked web list, Q-E01 and Q-M10 were reworded, and M02/M06/M11 still cite dictionaries that are not registered. The current instrument therefore scores 11 anchor questions and 4 abstention tests; a full re-review of the 24-question set belongs to the evaluation task.

Three questions need rewording rather than new sources: the sea-area and operation-type production trend, which the yearbooks publish by sea area and gear but not by operation type; the production, landed-weight and effort definitions, of which only production has an official definition; and the combined production-and-vessel-count question, which mixes a published indicator with an unpublished one.

The unanswerable questions remain abstention candidates; the current instrument runs four of them (Q-E07, Q-E11, Q-M07 and Q-M08).

## 8b. Gap audit: covered or unattainable, never duplicated

| Gap | Outcome |
|---|---|
| Logbook fields | Partly covered: `POL-STD-010` articles 50-53 give the obligation; the complete field list has no public source |
| Port classes for 2018-2019 | Not covered: the plan and the recognition proposal were removed on 2026-11-03; the yearbook tables themselves do not exist |
| Landed weight and fishing effort | International definition held (`STD-CWP-043`); Chinese official definition still missing. Only production is defined domestically (`DICT-STAT-013`, `DICT-STAT-040`), and the CWP pages are English and outside the index |
| Metadata and quality rules | No public source |
| Remaining 2025 tables | Source in hand (`STAT-YB-2026`); extraction work, not a new source |

Two international references were registered on 2026-11-01 for the definition gap; every other gap is either covered by an acquired source or has no public source, and no covered item is duplicated.

## 9. Local core CSV

The local extraction has **3,126 rows**: 3,037 for 2017–2024 (capture 1,665, vessels 1,116, population 128, marine capture value 32 and coastal ports 96) plus 89 for 2025 in the same indicator families — capture by sea area and gear, capture vessels by operation type, the five coastal port classes and three population indicators, with the three derived South China Sea rows. The 2025 block is still a sample: species, power and length bands and value are not extracted. The remaining 54 transcribed 2025 values (output and aquaculture totals, the port total, breed farms and household/township/village counts) fall outside the five indicator families and are kept in a local extras file rather than the core table. Every row validates against the dimensions in `configs/statistics.yaml（已移除）`. It preserves blanks, source locators and SHA-256; no values are published. Validation and coverage reports are in the local run root. The table is copied to the data root as `statistics/core-indicators-v3.csv` and is queryable on this machine through `scs-fkb stats`, which returns rows with edition and table citations; the public repository keeps only the schema and the query layer.

The 2025 block was checked against China Statistical Yearbook 2026 table 12-15: twelve compared cells match exactly, and the national yearbook's marine capture column equals marine capture plus distant-water output in the fisheries yearbook.

## 9a. V2 snapshots and parallel build

The P10 ingestion path does not touch the live v1 store. It copies every acquired
source into a content-addressed snapshot tree under the local data root:

```text
$SCS_FKB_DATA_ROOT/v2/snapshots/<source_id>/<source_hash>/
$SCS_FKB_DATA_ROOT/v2/snapshots.json
$SCS_FKB_DATA_ROOT/v2/processed/{documents,parents,chunks}.jsonl
$SCS_FKB_DATA_ROOT/v2/processed/manifest.json
```

- Single-file sources are SHA-256-verified against the register before copying.
- Directory sources (yearbook editions) get a per-file manifest and a tree hash;
  their register hash is an edition manifest, so they are marked
  `verified: false` rather than falsely claiming a tree-hash match.
- The build is incremental: a document whose source hash, loader plan, governance
  metadata or chunking config is unchanged is skipped. A changed document is
  rebuilt; a document removed from the pipeline is removed from the v2 store; a
  parse failure is quarantined with a reason.
- The v2 store contains 42 documents, 935 parent chunks and 1014 child chunks for
  the configured main index, with 0 lost page/section anchors against v1.
- Snapshots, parents, chunks and the manifest stay outside the public repository.

The build command is `PYTHONPATH=src python3 scripts/build_v2.py`; it writes a
private report under the run root. Optional Docling/trafilatura adapters live in
`requirements-rag.txt` and are not required by CI.

## 10. Licence and sensitivity policy

| Case | Action |
|---|---|
| `license: unknown` or `sensitivity: unknown` | Hold; do not ingest or index |
| `public` | Policy documents; may be used under the project's normal rules |
| `internal` | Yearbooks; owner-confirmed official/authorized; local use only; no public values |
| `restricted` | Local only; never send to an external model API |
| AIS/VMS sample | Licence and compliance review first; desensitise; keep only necessary fields |
| Personal information | Aggregate or anonymise; never commit or send externally |
| Copyrighted literature | Not registered in the current phase |

## 11. Data and artifact boundary

- Source files, core CSVs and indexes belong in the local data root (`SCS_FKB_DATA_ROOT`), outside the repository.
- Run artifacts belong in the local run root (`SCS_FKB_RUN_ROOT`), outside the repository.
- The public repository contains no data values, indexes, run outputs or state databases.
- Details: [data-policy.md](data-policy.md).

## 12. Gaps and next steps

1. The sufficiency review is done for the 2026-11-01 draft: ten questions answerable, six partial and eight abstention tests (section 8a); the current instrument scores 11 anchors and 4 abstention tests.
2. Diff the registered People's Daily text against the npc.gov.cn page when that site is reachable again; the 2026-10-31 WAF block and the attempts are recorded in the register.
3. The definition sources close `DICT-STAT-013`; the standards (including GB/T 5147—2026), the permit form and the permit regulation closed the logbook candidate; the deferred candidates were removed and the register has none.
4. Use the 2018 port plan as the port baseline and record the classification difference when extending the core CSV to ports.
5. Extract the remaining 2026 tables, starting with capture by species (pages 41-43).
6. Map the 2018 port-plan classes to the yearbook port classes when the core table is extended to ports.
7. The sufficiency verdict was accepted on 2026-11-01; the retrieval pipeline stays deferred by owner decision.
8. Build a bilingual term layer (Chinese term to CWP concept) before indexing `STD-CWP-043`; until then the definitions are citable but unreachable from the Chinese question set.

## 13. References

- [Corpus register](../configs/corpus.yaml)
- Statistics schema（已移除）
- [Data schema](../configs/schema.yaml)
- [Data policy](data-policy.md)
- [Project plan](plan.md)
- [Project scope](../PROJECT.md)


## 5m. Acceptance batch (2026-11-07)

Fourteen documents that the private acceptance instrument cites but the corpus
lacked were captured, hashed and registered. Eight came from national or
provincial publishers on HTTPS; two needed a plain-HTTP capture because the
publisher serves no TLS (recorded in the entry notes); one municipal notice and
three peer-reviewed papers are B- or C-tier as the register rules require.

| Source | Document | Tier | Indexed |
|---|---|---|---|
| POL-LAW-097 | 海上交通安全法（2021年修订） | A | yes |
| POL-LAW-098 | 海洋环境保护法（2023年修订） | A | yes |
| POL-LAW-099 | 野生动物保护法（2022年修订） | A | yes |
| POL-LAW-100 | 行政处罚法（2021年修订） | A | no — enables over-answers on refusal tests |
| POL-REG-101 | 渔业船舶登记办法（2019年修订） | A | yes |
| POL-GEAR-102 | 禁止使用十三种渔具的通告 | A | yes |
| POL-PEN-103 | 立案追诉标准（一） | A | yes |
| STD-WQ-104 | GB 3097-1997 海水水质标准 | A | no — water-quality text answers fish-abundance questions |
| PAPER-105 | 南海区拖网渔业发展趋势 | B | no — reference layer |
| PAPER-106 | 南海北部鸢乌贼栖息地适宜性 | B | no — reference layer |
| PAPER-107 | ENSO 对南海北部鱼类丰度的影响 | B | no — reference layer |
| POL-HN-108 | 三沙海域鸢乌贼专项捕捞方案 | A | no — boundary reference only |
| POL-QZ-109 | 钦州市2026年伏季休渔通告 | C | no — ranks above the national notice |
| POL-GD-110 | 广东省重点保护水生野生动物名录 | A | no — page carries navigation only |

Seven instruments had no official public text and are recorded as exclusions:
the two fishing-vessel inspection rules (draft or print editions only), the
shellfish-toxin standard (no official host publishes the text), the marine
heatwave classification (still a standard project, 20251136-T-418), the habitat
paper behind a bot wall, the Guangdong 2026 closure plan (only municipal notices
and a WeChat post quote it) and the Guangxi protected-species list (the registry
link resolves to an administrative service guide).

### Gate results

The larger corpus shifts BM25 scores, so the staging A/B re-calibrated the
answer gate from `min_score 19.0 / min_matched 3` to `23.0 / 4`; without it the
original anchors fell to 15–16 of 19. Six documents are indexed and the rest
stay registered.

| Gate | Before | After |
|---|---|---|
| v1 anchors (dev / test) | 19/19, 12/12 | 19/19, 12/12 |
| v1 abstention (of 11) | 8 | 8 |
| v1 false refusals | 2 | 2 |
| v2 dev correctness | 0.8945 | 0.8776 |
| v2 citation / recall / abstention | 1.0 / 0.9667 / 0.90 | 1.0 / 0.9625 / 0.90 |
| Acceptance answer rate | 0.4453 | 0.4590 |
| Acceptance point coverage | 0.1675 | 0.1766 |
| Acceptance citation accuracy | 0.1659 | 0.1706 |
| Acceptance misanswer rate | 0.3143 | 0.3286 (+1.43 pp, within the 2 pp tolerance) |

Indexes: v1 `686bc13a5ddc`, 1,661 chunks; v2 `59c70969e461`, 48 documents and
1,486 chunks. The service answer gate still uses its own 19.0/3 thresholds; the
mismatch with the corpus gate is the next answer-contract task.


## 5n. Batch 2 registration and deferred indexing (2026-11-07)

Eight further documents were captured and registered (register 91 → 99 sources):
the 2024 marine ecological bulletin, the sea-turtle action plan, the
Indo-Pacific humpback dolphin action plan, the small-vessel inspection rules,
the wildlife-crime judicial interpretation, the criminal-law text, the Guangxi
vessel-upgrading policy explainer and the seawater-quality assessment
regulation. Twenty-four other missing instruments were attempted and recorded:
several have no standalone public text (the logbook and vessel-quota rules live
inside 渔业捕捞许可管理规定; the minimum-size regime is the 2018 notice already
indexed), several exist only as drafts (hypoxia, heatwave, inspection rules), and
a few are policy-excluded (marine-ranch material).

**The eight registered documents are not indexed.** The staging A/B showed that
indexing the batch under the current 19.0/3 answer gate lifts the refusal
misanswer from 0.2571 to 0.3714–0.4000 and lowers citation accuracy; the index was
restored to the 48-document baseline and the 512 run returned to point 0.1684,
citation 0.3810 and misanswer 0.2571. Indexing is deferred until the answer gate
is aligned and re-tested (retrieval task).

## 5o. Chunk labels and recall baseline (2026-11-08)

Every child chunk now carries a section label: the article number in its first 80
characters, else the section heading, else `p.N`. This removes the 171 section-less
chunks that made citations unresolvable. Retrieval recall@10 on the 392 answerable
questions with mapped documents is 0.834 (hybrid), 0.776 (dense) and 0.753 (BM25);
the measurement script and artifacts are under the run root.

## 5p. Batch-2 documents indexed, term ceiling 0.8556 (2026-11-09)

Ten previously registered documents were indexed under the current refusal path
(the sufficiency judge keeps misanswer at 0.0857): the eight batch-2 documents plus
行政处罚法 and GB 3097. Indexed documents 48 → 58; chunks 1,486 → 2,412; the
term-level evidence ceiling rises 0.8281 → 0.8556. The dump arm moves
0.6518 → 0.6574 coverage, 0.1053 → 0.2105 basis, citation within 1 pp.

Batch 3 captured two more documents (a trawl paper and the Guangdong port-fee
notice) but neither is indexed: the paper duplicates a batch-1 snapshot, and the
port-fee notice lifts misanswer to 0.1143 for +0.4 pp coverage.
