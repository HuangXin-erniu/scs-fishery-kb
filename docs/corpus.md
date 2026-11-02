# Corpus Inventory

- Status: data preparation and corpus discovery. Nine yearbook editions, six national bulletins, the China Statistical Yearbook 2026 and twenty-six legal and technical documents are acquired, including two international reference sources; three candidates remain (all deferred). The local core CSV has 3,126 rows and stays outside the public tree. No parsing or indexing in this phase.
- Register: [configs/corpus.yaml](../configs/corpus.yaml)
- Indicator schema: [configs/statistics.yaml](../configs/statistics.yaml)
- Date: 2026-11-01

## 1. Purpose and scope

This inventory covers the knowledge layer: fishing-vessel operations and catch statistics, vessel/voyage data dictionaries, ocean and fishery product descriptions, fishery bulletins and historical records, laws and standards, and data dictionaries.

It does **not** include raw environmental grids, reanalysis data, forecast rasters or products, full AIS/VMS tracks, or unlicensed material. No data values are published in this repository.

## 2. Method

1. Define nine corpus types and register each source with title, publisher, year, type, format, location, licence, sensitivity, status, priority, volume, update frequency, hash and acquisition notes.
2. Hold every source whose licence or sensitivity is `unknown`.
3. Acquire only from official or owner-confirmed authoritative channels; record the retrieval path, date and SHA-256.
4. Keep source files in the local data root; the public register contains metadata, hashes and coverage counts only.
5. Do not parse or index sources in this phase.

## 3. Types

| Type | Name (zh) | Sources | Description |
|---|---|---:|---|
| `statistical_yearbook` | 统计年鉴 | 16 | Official annual statistics and indicator tables |
| `operations` | 作业知识 | 1 | Fishing methods, gear, vessel operations, logbooks and permit conditions |
| `law` | 法律 | 1 | National law adopted by the legislature |
| `regulation` | 行政法规/规章/地方性法规 | 14 | Administrative regulations, departmental rules and local regulations |
| `notice` | 通告/公告 | 6 | Official notices, announcements and seasonal measures |
| `standard` | 标准/规范 | 7 | National, industry or provincial standards and operational norms |
| `fishery_product` | 渔情/海况产品说明 | 4 | Product descriptions, fishery bulletins and historical records |
| `data_dictionary` | 数据字典 | 8 | Field definitions, indicator definitions, metadata and quality rules |
| `plan` | 规划/方案 | 1 | Official plans, programmes and construction layouts |

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

The bulletin series `STAT-BULL-025` and `STAT-BULL-028`–`STAT-BULL-032` covers data years 2020–2025 (published 2021–2026). Each bulletin reports national totals only — no provincial or South China Sea breakdown — so the series extends the record in time but does not replace the yearbook editions. Values stay local.

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
| `POL-PORT-037` | `notice` | national | Central and first-class fishing-port recognition list | acquired; 12 central and 2 first-class ports, proposed 2025-01-15 |
| `POL-GEAR-016` | `notice` | national | Minimum-mesh system for permitted and transitional gear, 2013 | acquired; in force 2014-06-01, annexes registered separately |
| `POL-SPEC-041` | `notice` | national | Closed-season special-permit arrangement for 2026 | acquired; permits Sthenoteuthis oualaniensis in the South China Sea for Guangxi and Hainan |
| `POL-PLAN-038` | `plan` | national | National coastal fishing-port construction plan, 2018–2025 | acquired |

The legal corpus now covers the national law, its implementing rules, vessel inspection, the resource levy, the fishing-permit rules, the seasonal closure and the 2026 special-permit arrangement, plus the Guangdong, Guangxi and Fujian regulations. Each document records its publisher, revision history, article count and SHA-256. Article counts: Fisheries Law 90, implementing rules 42, vessel inspection 40, levy measures 18, permit regulation 59, closure notice 4 sections, special-permit notice 3 annexes, Guangdong fishery 47, Guangdong port and vessel 44, Guangxi implementation 48, Guangxi port and vessel 37, Fujian implementation 61, Fujian port and vessel 46. The 2026 notice is registered from the ministry's OFD attachment, a 22-page XML container whose text layer extracts without OCR; it allows Sthenoteuthis oualaniensis permits in the South China Sea north of 12°N (36 Guangxi vessels and 2,500 t from 20 June to 5 August; 70 Hainan vessels and 5,000 t from 1 May to 15 August; mask net 35 mm) and adds 26 Hainan auxiliary vessels. Its operation-type permits cover only the Yellow and East China Seas.

The Fisheries Law text is the owner-supplied DOCX of the official 人民日报 publication. The article openings were cross-checked against the electronic edition before the duplicate copies were removed on 2026-10-31; the registered DOCX is now the single retained text. The official ministry PDF edition of the fishing-permit regulation (29 pages) is kept beside the registered HTML as a format copy; its articles 50–53 carry the logbook obligation.

## 5a. Acquired standards and operations supplements

| Source | Type | Document | What it answers |
|---|---|---|---|
| `POL-GEAR-033` | `standard` | Minimum mesh sizes for permitted marine capture gear | Gear classes and minimum mesh by sea area and target species |
| `POL-GEAR-034` | `standard` | Minimum mesh sizes for transitional gear | Trawl, gillnet, purse seine, stow-net, cage and trap classes |
| `OPS-STD-035` | `standard` | SC/T 9460—2025 marine capture information sampling survey | Defines marine capture information and sample vessels; sets monthly collection and quality control; cites GB/T 5147—2003 for gear classification |
| `OPS-FORM-036` | `operations` | Approved-operation block, form and filling instructions | Nine operation types, at most two operation methods and two gear names, minimum mesh size, quota |
| `OPS-STD-039` | `standard` | GB/T 5147—2026 fishing-gear classification, naming and codes | The national classification that maps yearbook gear groups and permit operation types |
| `STD-SC-042` | `standard` | SC/T aquatic-industry standards in scope (17 held) | Gear and mesh, vessel management data, fishing ports, fishery statistics and surveys, resource surveys and terminology |

The mesh tables and the form are annexes 1, 2 and 3 of the 2013 notice `POL-GEAR-016`, which entered into force on 2014-06-01 and repealed the 2003 notice. SC/T 9460—2025 was published 2025-12-09 and takes effect 2026-05-01; GB/T 5147—2026 was published 2026-02-27 and takes effect 2026-09-01, replacing the 2003 edition. `STD-SC-042` is a series entry: the national standards platform lists 809 current SC/T standards and 17 fall inside the project scope with a public text, which the project holds as image-only reference copies (`configs/sc-standards.yaml`). The seven in-scope standards without a public text were excluded from the project on 2026-11-01. SC/T 9460—2025 stays registered as `OPS-STD-035` and is not duplicated in the series; aquaculture, feed, disease, processing, hull-construction, ship-equipment and freshwater-survey series are out of scope.

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
| `STD-ASFIS-044` | FAO Fisheries and Aquaculture Division | The ASFIS 2026.1 species list: 3-alpha codes, ISSCAAP groups, scientific names and common names in six languages, 2,695 with Chinese names | Not indexed: a lookup table rather than narrative text |
| `STD-MUR-045` | NASA JPL PO.DAAC | The 0.01° daily MUR foundation SST product description: algorithm, latency and licence | Indexed in the product reference collection, not the main index |
| `STD-OLCI-046` | EUMETSAT | The OLCI marine user handbook: L1B/L2 marine products and the retrievals behind the 4 km chlorophyll product | Indexed in the product reference collection |
| `DICT-GFW-047` | Global Fishing Watch | Apparent fishing effort versus fishing events and how positions are grouped | Indexed in the product reference collection |
| `DICT-GFW-048` | Global Fishing Watch | The Events API documentation for port visits, encounters, loitering and fishing events | Indexed in the product reference collection |
| `STD-CMEMS-049` | Mercator Ocean International | The GLOBAL_MULTIYEAR_PHY_001_030 user manual: the 1/12° background physics layer | Indexed in the product reference collection |
| `STD-HY1-056` | 国家卫星海洋应用中心 | The HY-1C/D payload capability page: coverage cycle, ground sample distance, swath and the retrieved ocean-colour variables | Indexed in the product reference collection; Chinese-language |

Both carry the FAO open-access licence CC BY-NC-SA 3.0 IGO, so they stay local and nothing is copied into this repository. A project-authored terminology bridge in [configs/glossary-bridge.yaml](../configs/glossary-bridge.yaml) maps five Chinese statistical terms to the CWP concepts and feeds a reference channel, so a Chinese definition question can reach these English pages without joining the main index. They are the international counterpart of definitions the domestic yearbooks leave implicit: `DICT-STAT-013` and `DICT-STAT-040` define production, while landed weight and fishing effort only have the CWP definitions. A Chinese official definition is still missing, and the English pages cannot be reached by the Chinese question set until a bilingual term layer exists. Per-page hashes live in [configs/cwp-handbook.yaml](../configs/cwp-handbook.yaml). Five product and method documents for the remote data stack joined the register on 2026-11-02: the MUR SST product page (CC BY 4.0), the EUMETSAT OLCI marine handbook, the GFW effort-versus-events FAQ, the GFW Events API documentation (Apache 2.0) and the CMEMS product user manual. They fill the previously empty `fishery_product` type and explain the data the remote forecasting work actually uses; all five are indexed in the product reference collection and scored as Q-E08 and Q-M09. A sixth, `STD-HY1-056`, joined on 2026-11-02 as the Chinese counterpart of those descriptions and now forms part of the Q-M09 expectation.

## 5d. Statistical governance and monitoring

| Source | Publisher | Status on 2026-11-02 | What it provides |
|---|---|---|---|
| `POL-STAT-050` | 农业农村部（原农业部） | Current; no repeal found (农渔发〔2010〕5号) | Duties, submission and quality rules for fishery statistics: the process behind the yearbook |
| `POL-STAT-051` | 国家统计局 / 农业农村部 | Current; 国统制〔2024〕120号, valid to June 2027 | The 2024 fishery statistics survey system, replacing the 2021 approval that expired in February 2024 |
| `POL-YJ-052` | 农业农村部办公厅 | Latest publicly posted full text (农办渔〔2018〕30号) | Agencies, annual cadence and format of fishery monitoring work |
| `POL-VMS-053` | 农业农村部 | Current; repealed the 2014 measures | Distant-water vessel position monitoring duties, not near-shore VMS fields |
| `STD-ECERT-054` | 农业农村部办公厅 | Current (2025) | Electronic certificate standards C 0402—2024, C 0403—2024 and C 0374—2024 for quota approval, ownership registration and nationality |
| `POL-YJ-057` | 农业农村部渔业渔政管理局 | Newest publicly posted full text: 农渔科函〔2021〕21号, 2021-04-15 | The 2020 fishery-monitoring circular: annual cadence, responsible bodies and the data-quality machinery of 渔情监测统计 |

All six are indexed in the policy reference collection; the currency check changed two candidates. The 2021 survey system has expired, so `POL-STAT-051` registers the 2024 text with its new approval number. The 2024 monitoring letter (农渔科函〔2025〕87号) is referenced by provincial news but its full text is not published, so `POL-YJ-052` is the latest public full text and says so. SC/T 9403-2025 turned out to be already held inside the SC/T series (`STD-SC-042`, 37 pages), so it was not registered twice. Near-shore VMS definitions and a data-sharing metadata rule remain uncovered, and Q-M02, Q-M06 and Q-M11 stay out of reach. The 2024 monitoring letter (农渔科函〔2025〕87号) is quoted by provincial sites but not published in full; the ministry gazette index exposes no file list and the national marine forecast portal is a single-page service without a downloadable product document, so the 2020 circular is the newest publicly posted text and Q-M07 stays uncovered.

## 5e. Crew management and the Chinese ocean-colour description

| Source | Publisher | Currency | What it provides |
|---|---|---|---|
| `POL-CREW-055` | 农业农村部 | Current; the 2014 order was amended in 2017 and 2022, registered from the 2022-01-07 republication | Certificate grades, the minimum manning table, the captain duty to fill the fishing log and the penalty range for crew and owner breaches |
| `STD-HY1-056` | 国家卫星海洋应用中心 | The current description of the in-orbit HY-1C/D pair, published 2018-11-02 | Coverage cycle (one day for a single satellite, half a day for the pair), ground sample distance (1100 m for the ocean-colour scanner, 50 m for the coastal-zone imager), a 2900 km swath, the band table and the retrieved variables including chlorophyll and sea surface temperature |

Two holes from the corpus audit close here. The crew rule turns the crew line from a provincial principle into a national rule: the Guangdong, Guangxi and Fujian port-and-vessel regulations state crew and safety duties in general terms, while `POL-CREW-055` carries the manning table and the certificate grades. The HY-1C/D page is the Chinese counterpart of the English MUR and OLCI documentation; it is a payload capability page rather than a product user manual, so it explains what the sensors measure and how often, not how a product is validated.

Both are routed through reference collections. The crew rule sits in the policy collection, which already passes the raw Chinese question. The ocean-colour page sits in the product collection, and the channel had to change to reach it: the product channel previously searched only with the bridged English concepts, so a Chinese-language document could never rank. It now searches with the concepts plus the original question, while the bridged concepts still decide whether the channel fires at all. `Q-E08` still returns MUR first; `Q-M09` now also expects `STD-HY1-056`, because a Chinese question about spatio-temporal resolution should reach the Chinese page.

Hainan remains the open jurisdiction: the provincial government page carries the 2008 amendment and is marked 已修改, and the national law database confirms the 2013 revision is in force but serves the body only through a script-driven page and a signed attachment this network cannot extract. No superseded text is registered, so the Hainan gap stays open with its evidence rather than being filled with a stale copy.

Four retrieval terms were added to the bridge in the same task: 水色 to ocean colour, 覆盖周期 to coverage cycle, 重访 to revisit and 幅宽 to swath. Before the addition, a question phrased only with those words returned an empty product block because the channel fires on bridged concepts; after it, 海洋水色产品的覆盖周期是多少？ and 海洋水色产品的幅宽与重访周期是多少？ both return `STD-HY1-056`, while `Q-E08` still leads with MUR and the four abstention tests are unchanged. The bridge is a retrieval mapping, not a translation, and each entry says so in its note.

## 6. Candidate sources

| ID | Type | Title | Priority | Disposition |
|---|---|---|---|---|
| `VMS-DICT-003` | `data_dictionary` | Vessel/voyage data dictionary | P2 | defer |
| `VMS-SAMPLE-004` | `data_dictionary` | Desensitised voyage sample description | P2 | defer |
| `DICT-META-014` | `data_dictionary` | Metadata and data-quality rules | P2 | defer |

The four environment and fishery-product candidates were removed on owner instruction on 2026-11-01; the fishery_product type stays defined with no sources. The logbook candidate was closed on 2026-11-01: articles 50-53 of `POL-STD-010`, the approved-operation block `OPS-FORM-036` and SC/T 9460-2025 already cover the record fields and the reporting duty, so no separate source is acquired. `OPS-STAT-001`, the generic yearbook candidate, was removed from the register because the editions supersede it. All three remaining candidates are deferred, which keeps them in the register but out of the current phase. Papers and reports were removed from the register because they are not accepted as authoritative project sources at this stage.

## 7. Status summary

| Metric | Value |
|---|---:|
| Corpus types | 9 |
| Registered sources | 58 |
| Acquired sources | 55 |
| Remaining candidates | 3 |
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

- Coastal-port infrastructure is missing from the yearbooks for data years 2018 and 2019: the 838-file inventory confirms that the 2019 and 2020 editions contain no infrastructure table. The 2018 national port plan (POL-PLAN-038) supplies a 2018 baseline with named central and first-class ports, and the 2025 recognition list (POL-PORT-037) adds 14 more, but the plan's port classes are not identical with the yearbook table and the 2025 list is still a proposal, so neither can be pasted into the core CSV without a mapping note.
- Data year 2025 is sampled, not complete: the six transcribed tables cover output, capture by sea area and gear, capture vessels by operation type, ports and population, while the species breakdown, power and length bands, value and the remaining tables are still to be extracted from the scan.
- The 2017 and 2021 source tables have only 沿海中心渔港 and 沿海一级渔港; the later tables add class 2, class 3 and unrated ports.
- The vessel-length proxy is missing for data year 2024; the 2025 edition dropped the marine vessel-length table and keeps only the all-vessel and inland tables. The gap is accepted rather than filled from a non-comparable table.
- The vessel-length table is a marine production-vessel proxy, not capture-only.
- The 2025 edition renumbers and reorganises the vessel tables, adding marine capture-vessel tables by power and operation type; compare editions by table title, not by table number.
- No registered edition publishes capture production by operation type; production is available by sea area, gear group and species only.
- The published South China Sea column includes Fujian in data years 2017–2020 and excludes it from 2021 onward. The CSV stores the published value, the Guangdong/Guangxi/Hainan subtotal and the difference.

## 8a. Sufficiency review

The 24 draft questions were checked against the registered sources on 2026-11-01: **10 are answerable, 6 partially answerable and 8 not answerable**. Every unanswerable question maps to material outside the registration scope (vessel/voyage dictionaries and the excluded environment and fishery-product sources); nothing in the P1 scope is blocked.

Three questions need rewording rather than new sources: the sea-area and operation-type production trend, which the yearbooks publish by sea area and gear but not by operation type; the production, landed-weight and effort definitions, of which only production has an official definition; and the combined production-and-vessel-count question, which mixes a published indicator with an unpublished one.

The eight unanswerable questions stay as abstention tests until the deferred sources are acquired.

## 8b. Gap audit: covered or unattainable, never duplicated

| Gap | Outcome |
|---|---|
| Logbook fields | Partly covered: `POL-STD-010` articles 50-53 and `OPS-FORM-036` give the obligation and the approved-operation fields; the complete field list has no public source |
| Port classes for 2018-2019 | Covered: `POL-PLAN-038` supplies the 2018 baseline and `POL-PORT-037` the 2025 proposal; the yearbook tables themselves do not exist |
| Landed weight and fishing effort | International definition held (`STD-CWP-043`); Chinese official definition still missing. Only production is defined domestically (`DICT-STAT-013`, `DICT-STAT-040`), and the CWP pages are English and outside the index |
| Metadata and quality rules | No public source |
| Remaining 2025 tables | Source in hand (`STAT-YB-2026`); extraction work, not a new source |

Two international references were registered on 2026-11-01 for the definition gap; every other gap is either covered by an acquired source or has no public source, and no covered item is duplicated.

## 9. Local core CSV

The local extraction has **3,126 rows**: 3,037 for 2017–2024 (capture 1,665, vessels 1,116, population 128, marine capture value 32 and coastal ports 96) plus 89 for 2025 in the same indicator families — capture by sea area and gear, capture vessels by operation type, the five coastal port classes and three population indicators, with the three derived South China Sea rows. The 2025 block is still a sample: species, power and length bands and value are not extracted. The remaining 54 transcribed 2025 values (output and aquaculture totals, the port total, breed farms and household/township/village counts) fall outside the five indicator families and are kept in a local extras file rather than the core table. Every row validates against the dimensions in `configs/statistics.yaml`. It preserves blanks, source locators and SHA-256; no values are published. Validation and coverage reports are in the local run root. The table is copied to the data root as `statistics/core-indicators-v3.csv` and is queryable on this machine through `scs-fkb stats`, which returns rows with edition and table citations; the public repository keeps only the schema and the query layer.

The 2025 block was checked against China Statistical Yearbook 2026 table 12-15: twelve compared cells match exactly, and the national yearbook's marine capture column equals marine capture plus distant-water output in the fisheries yearbook.

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

1. The sufficiency review is done: ten questions are answerable, six partial and eight are abstention tests (section 8a).
2. Diff the registered People's Daily text against the npc.gov.cn page when that site is reachable again; the 2026-10-31 WAF block and the attempts are recorded in the register.
3. The definition sources close `DICT-STAT-013`; the standards (including GB/T 5147—2026), the permit form and the permit regulation closed the logbook candidate, and the three deferred candidates stay out of the current phase.
4. Use the 2018 port plan as the port baseline and record the classification difference when extending the core CSV to ports.
5. Extract the remaining 2026 tables, starting with capture by species (pages 41-43).
6. Map the 2018 port-plan classes to the yearbook port classes when the core table is extended to ports.
7. The sufficiency verdict was accepted on 2026-11-01; the retrieval pipeline stays deferred by owner decision.
8. Build a bilingual term layer (Chinese term to CWP concept) before indexing `STD-CWP-043`; until then the definitions are citable but unreachable from the Chinese question set.

## 13. References

- [Corpus register](../configs/corpus.yaml)
- [Statistics schema](../configs/statistics.yaml)
- [Data schema](../configs/schema.yaml)
- [Data policy](data-policy.md)
- [Project plan](plan.md)
- [Project scope](../PROJECT.md)
