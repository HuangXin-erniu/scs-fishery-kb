# Corpus Inventory

- Status: data preparation and corpus discovery. Nine yearbook editions, six national bulletins, the China Statistical Yearbook 2026 and twenty-two legal and technical documents are acquired; eight candidates remain (one to acquire, seven deferred). The local core CSV has 3,177 rows and stays outside the public tree. No parsing or indexing in this phase.
- Register: [configs/corpus.yaml](../configs/corpus.yaml)
- Indicator schema: [configs/statistics.yaml](../configs/statistics.yaml)
- Date: 2026-10-31

## 1. Purpose and scope

This inventory covers the knowledge layer: fishing-vessel operations and catch statistics, vessel/voyage data dictionaries, ocean and fishery product descriptions, fishery bulletins and historical records, laws and standards, and data dictionaries.

It does **not** include raw environmental grids, reanalysis data, forecast rasters or products, full AIS/VMS tracks, or unlicensed material. No data values are published in this repository.

## 2. Method

1. Define eight corpus types and register each source with title, publisher, year, type, format, location, licence, sensitivity, status, priority, volume, update frequency, hash and acquisition notes.
2. Hold every source whose licence or sensitivity is `unknown`.
3. Acquire only from official or owner-confirmed authoritative channels; record the retrieval path, date and SHA-256.
4. Keep source files in the local data root; the public register contains metadata, hashes and coverage counts only.
5. Do not parse or index sources in this phase.

## 3. Types

| Type | Name (zh) | Sources | Description |
|---|---|---:|---|
| `statistical_yearbook` | 统计年鉴 | 15 | Official annual statistics and indicator tables |
| `operations` | 作业知识 | 2 | Fishing methods, gear, vessel operations, logbooks and permit conditions |
| `law` | 法律 | 1 | National law adopted by the legislature |
| `regulation` | 行政法规/规章/地方性法规 | 10 | Administrative regulations, departmental rules and local regulations |
| `notice` | 通告/公告 | 2 | Official notices, announcements and seasonal measures |
| `standard` | 标准/规范 | 3 | National, industry or provincial standards and operational norms |
| `fishery_product` | 渔情/海况产品说明 | 4 | Product descriptions, fishery bulletins and historical records |
| `data_dictionary` | 数据字典 | 5 | Field definitions, indicator definitions, metadata and quality rules |
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
| `POL-CLOS-015` | `notice` | national | Seasonal closure notice, 2023 | acquired |
| `POL-GD-021` | `regulation` | guangdong | Guangdong fishery management regulations, 2019 amendment | acquired |
| `POL-GD-022` | `regulation` | guangdong | Guangdong fishing-port and fishing-vessel regulations, 2020 amendment | acquired |
| `POL-GX-023` | `regulation` | guangxi | Guangxi measures implementing the Fisheries Law, 2016 amendment | acquired |
| `POL-GX-024` | `regulation` | guangxi | Guangxi fishing-port and fishing-vessel regulations, 2024 amendment | acquired |
| `POL-FJ-025` | `regulation` | fujian | Fujian measures implementing the Fisheries Law, 2019 amendment | acquired |
| `POL-FJ-026` | `regulation` | fujian | Fujian fishing-port and fishing-vessel regulations, 2010 amendment | acquired |
| `POL-PORT-037` | `notice` | national | Central and first-class fishing-port recognition list | acquired; 12 central and 2 first-class ports, proposed 2025-01-15 |
| `POL-GEAR-016` | `notice` | national | Minimum-mesh system for permitted and transitional gear, 2013 | acquired; in force 2014-06-01, annexes registered separately |
| `POL-PLAN-038` | `plan` | national | National coastal fishing-port construction plan, 2018–2025 | acquired |

The legal corpus now covers the national law, its implementing rules, vessel inspection, the resource levy, the fishing-permit rules and the seasonal closure, plus the Guangdong, Guangxi and Fujian regulations. Each document records its publisher, revision history, article count and SHA-256. Article counts: Fisheries Law 90, implementing rules 42, vessel inspection 40, levy measures 18, permit regulation 59, closure notice 4 sections, Guangdong fishery 47, Guangdong port and vessel 44, Guangxi implementation 48, Guangxi port and vessel 37, Fujian implementation 61, Fujian port and vessel 46.

The Fisheries Law text is the owner-supplied DOCX of the official 人民日报 publication. The article openings were cross-checked against the electronic edition before the duplicate copies were removed on 2026-10-31; the registered DOCX is now the single retained text. The official ministry PDF edition of the fishing-permit regulation (29 pages) is kept beside the registered HTML as a format copy; its articles 50–53 carry the logbook obligation.

## 5a. Acquired standards and operations supplements

| Source | Type | Document | What it answers |
|---|---|---|---|
| `POL-GEAR-033` | `standard` | Minimum mesh sizes for permitted marine capture gear | Gear classes and minimum mesh by sea area and target species |
| `POL-GEAR-034` | `standard` | Minimum mesh sizes for transitional gear | Trawl, gillnet, purse seine, stow-net, cage and trap classes |
| `OPS-STD-035` | `standard` | SC/T 9460—2025 marine capture information sampling survey | Defines marine capture information and sample vessels; sets monthly collection and quality control; cites GB/T 5147—2003 for gear classification |
| `OPS-FORM-036` | `operations` | Approved-operation block, form and filling instructions | Nine operation types, at most two operation methods and two gear names, minimum mesh size, quota |
| `OPS-STD-039` | `standard` | GB/T 5147—2026 fishing-gear classification, naming and codes | The national classification that maps yearbook gear groups and permit operation types |

The mesh tables and the form are annexes 1, 2 and 3 of the 2013 notice `POL-GEAR-016`, which entered into force on 2014-06-01 and repealed the 2003 notice. SC/T 9460—2025 was published 2025-12-09 and takes effect 2026-05-01; GB/T 5147—2026 was published 2026-02-27 and takes effect 2026-09-01, replacing the 2003 edition.

## 5b. Acquired definitions

| Source | Publisher | What it defines |
|---|---|---|
| `DICT-STAT-013` | 农业农村部渔业渔政管理局 | Appendix 3 of the 2024 fisheries yearbook: the water-product concept and scope, the reporting unit, the fresh-weight basis, the culture-versus-capture rule, product classes, and capture production by sea area (with the Bohai, Yellow, East China and South China Sea boundaries) and by gear group |
| `DICT-STAT-040` | 国家统计局 | Chapter-12 notes of the 2025 national yearbook: the national definition of water-product output as the final effective output of capture and culture, reported through fishery departments, fresh weight since 1996; no sea-area or gear split |

The two agree on the concept and differ in scope: the national note sets the headline indicator, while the fisheries appendix supplies the operational rules the sea-area and gear tables depend on.

## 6. Candidate sources

| ID | Type | Title | Priority | Disposition |
|---|---|---|---|---|
| `OPS-LOG-002` | `operations` | Logbook and fishing-record specification | P1 | acquire |
| `VMS-DICT-003` | `data_dictionary` | Vessel/voyage data dictionary | P2 | defer |
| `VMS-SAMPLE-004` | `data_dictionary` | Desensitised voyage sample description | P2 | defer |
| `ENV-SST-005` | `fishery_product` | Sea surface temperature product description | P2 | defer |
| `ENV-CHL-006` | `fishery_product` | Chlorophyll/current/wind product description | P2 | defer |
| `FCS-BULL-007` | `fishery_product` | Fishing-ground and season bulletin | P2 | defer |
| `FCS-REC-008` | `fishery_product` | Historical fishing-ground and season record | P2 | defer |
| `DICT-META-014` | `data_dictionary` | Metadata and data-quality rules | P2 | defer |

`OPS-STAT-001`, the generic yearbook candidate, was removed from the register because the eight editions supersede it. `acquire` marks a follow-up acquisition task; `defer` keeps the source in the register but out of the current phase. Papers and reports were removed from the register because they are not accepted as authoritative project sources at this stage.

## 7. Status summary

| Metric | Value |
|---|---:|
| Corpus types | 9 |
| Registered sources | 46 |
| Acquired sources | 38 |
| Remaining candidates | 8 |
| Yearbook editions | 9 |
| Yearbook data years | 2017–2025 |
| Yearbook files | 839 |
| Local core CSV rows | 3,177 |
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

The 24 draft questions were checked against the registered sources on 2026-11-01: **10 are answerable, 6 partially answerable and 8 not answerable**. Every unanswerable question maps to a deferred candidate source (vessel/voyage dictionaries, ocean and fishery-product descriptions, historical fishing-ground records); nothing in the P1 scope is blocked.

Three questions need rewording rather than new sources: the sea-area and operation-type production trend, which the yearbooks publish by sea area and gear but not by operation type; the production, landed-weight and effort definitions, of which only production has an official definition; and the combined production-and-vessel-count question, which mixes a published indicator with an unpublished one.

The eight unanswerable questions stay as abstention tests until the deferred sources are acquired.

## 9. Local core CSV

The local extraction has **3,177 rows**: 3,037 for 2017–2024 (capture 1,665, vessels 1,116, population 128, marine capture value 32 and coastal ports 96) plus 140 for 2025 covering six tables — output, capture by sea area, capture by gear, capture vessels by operation type, fishing ports and fishery population — for the national total and Guangdong, Guangxi and Hainan. The 2025 block is partial; species, power and length bands and value are still to be extracted. It preserves blanks, source locators and SHA-256; no values are published. Validation and coverage reports are in the local run root.

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
3. The definition sources close `DICT-STAT-013`; the standards (including GB/T 5147—2026), the permit form and the permit regulation cover most of `OPS-LOG-002`, and the seven deferred candidates stay out of the current phase.
4. Use the 2018 port plan as the port baseline and record the classification difference when extending the core CSV to ports.
5. Extract the remaining 2026 tables, starting with capture by species (pages 41-43).
6. Map the 2018 port-plan classes to the yearbook port classes and close the remaining candidate dispositions.
7. Do not plan or implement the retrieval pipeline until the owner accepts the review verdict.

## 13. References

- [Corpus register](../configs/corpus.yaml)
- [Statistics schema](../configs/statistics.yaml)
- [Data schema](../configs/schema.yaml)
- [Data policy](data-policy.md)
- [Project plan](plan.md)
- [Project scope](../PROJECT.md)
