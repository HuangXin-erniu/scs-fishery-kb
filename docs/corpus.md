# Corpus Inventory

- Status: data preparation and corpus discovery. Eight yearbook editions and three policy documents are acquired; nine candidates are dispositioned (two to acquire, seven deferred). The local core CSV has 3,037 rows and stays outside the public tree. No parsing or indexing in this phase.
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
| `statistical_yearbook` | 统计年鉴 | 8 | Official annual statistics and indicator tables |
| `operations` | 作业知识 | 1 | Fishing methods, gear, vessel operations, logbooks and permit conditions |
| `law` | 法律 | 1 | National law adopted by the legislature |
| `regulation` | 行政法规/规章/地方性法规 | 8 | Administrative regulations, departmental rules and local regulations |
| `notice` | 通告/公告 | 1 | Official notices, announcements and seasonal measures |
| `standard` | 标准/规范 | 0 | National, industry or provincial standards and operational norms |
| `fishery_product` | 渔情/海况产品说明 | 4 | Product descriptions, fishery bulletins and historical records |
| `data_dictionary` | 数据字典 | 4 | Field definitions, indicator definitions, metadata and quality rules |

## 4. Acquired yearbooks

All eight editions are owner-confirmed official/authorized Excel editions. The public metadata records edition, data year, file count and manifest SHA-256; values stay local.

| Source | Edition | Data year | Files | Format | Manifest SHA-256 (short) |
|---|---:|---:|---:|---|---|
| `STAT-YB-2018` | 2018 | 2017 | 86 | xlsx | `9b5ddea6` |
| `STAT-YB-2019` | 2019 | 2018 | 137 | xls | `025f4a43` |
| `STAT-YB-2020` | 2020 | 2019 | 140 | xls | `71d5033b` |
| `STAT-YB-2021` | 2021 | 2020 | 84 | xlsx | `edd634e9` |
| `STAT-YB-2022` | 2022 | 2021 | 85 | xlsx | `82b9b8bd` |
| `STAT-YB-2023` | 2023 | 2022 | 84 | xlsx | `e8cb6104` |
| `STAT-YB-2024` | 2024 | 2023 | 140 | xls | `dc4c7475` |
| `STAT-YB-2025` | 2025 | 2024 | 82 | xlsx | `8768019d` |

The 2024 edition is encrypted with the Excel default password; the originals are unchanged in `raw/STAT-YB-2024/`, and decrypted working copies are kept outside the public tree. The 2019, 2020 and 2024 editions use the older `.xls` layout.

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

The legal corpus now covers the national law, its implementing rules, vessel inspection, the resource levy, the fishing-permit rules and the seasonal closure, plus the Guangdong and Guangxi regulations. Each document records its publisher, revision history, article count and SHA-256. Article counts: Fisheries Law 90, implementing rules 42, vessel inspection 40, levy measures 18, permit regulation 59, closure notice 4 sections, Guangdong fishery 47, Guangdong port and vessel 44, Guangxi implementation 48, Guangxi port and vessel 37.

The Fisheries Law text is the owner-supplied DOCX of the official 人民日报 publication; 89 of its 90 article openings match the e-paper capture and the 90th differs only by the 新华社 tag. The e-paper HTML, the page-11 PDF and the earlier municipal reprint are retained in the data root as provenance copies.

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
| `DICT-STAT-013` | `data_dictionary` | Statistical indicator definitions | P1 | acquire |
| `DICT-META-014` | `data_dictionary` | Metadata and data-quality rules | P2 | defer |

`OPS-STAT-001`, the generic yearbook candidate, was removed from the register because the eight editions supersede it. `acquire` marks a follow-up acquisition task; `defer` keeps the source in the register but out of the current phase. Papers and reports were removed from the register because they are not accepted as authoritative project sources at this stage.

## 7. Status summary

| Metric | Value |
|---|---:|
| Corpus types | 8 |
| Registered sources | 27 |
| Acquired sources | 18 |
| Remaining candidates | 9 |
| Yearbook editions | 8 |
| Yearbook data years | 2017–2024 |
| Yearbook files | 838 |
| Local core CSV rows | 3,037 |
| Public values | 0 |

## 8. Core coverage

The coverage matrix uses the latest edition for each data year. Counts are table counts, not values.

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

Known gaps:

- Coastal-port infrastructure is missing for data years 2018 and 2019. The 838-file inventory confirms that the 2019 and 2020 editions contain no infrastructure table, so the gap cannot be filled from the registered corpus.
- The 2017 and 2021 source tables have only 沿海中心渔港 and 沿海一级渔港; the later tables add class 2, class 3 and unrated ports.
- The vessel-length proxy is missing for data year 2024; the 2025 edition dropped the marine vessel-length table and keeps only the all-vessel and inland tables. The gap is accepted rather than filled from a non-comparable table.
- The vessel-length table is a marine production-vessel proxy, not capture-only.
- The 2025 edition renumbers and reorganises the vessel tables, adding marine capture-vessel tables by power and operation type; compare editions by table title, not by table number.
- No registered edition publishes capture production by operation type; production is available by sea area, gear group and species only.
- The published South China Sea column includes Fujian in data years 2017–2020 and excludes it from 2021 onward. The CSV stores the published value, the Guangdong/Guangxi/Hainan subtotal and the difference.

## 9. Local core CSV

The local extraction has **3,037 rows** for 2017–2024: capture 1,665, vessels 1,116, population 128, marine capture value 32 and coastal ports 96. It preserves blanks, source locators and SHA-256; no values are published. Validation and coverage reports are in the local run root.

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

1. Review the local core CSV and decide whether the indicator coverage is sufficient.
2. Diff the registered People's Daily text against the npc.gov.cn page when that site is reachable again; the 2026-10-31 WAF block and the attempts are recorded in the register.
3. Acquire `DICT-STAT-013` and seek a public official `OPS-LOG-002`; the seven deferred candidates stay out of the current phase.
4. Do not plan or implement the retrieval pipeline until the sufficiency review is accepted.

## 13. References

- [Corpus register](../configs/corpus.yaml)
- [Statistics schema](../configs/statistics.yaml)
- [Data schema](../configs/schema.yaml)
- [Data policy](data-policy.md)
- [Project plan](plan.md)
- [Project scope](../PROJECT.md)
