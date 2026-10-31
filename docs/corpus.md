# Corpus Inventory

- Status: data preparation and corpus discovery. Eight yearbook editions and three policy documents are acquired; ten candidates remain. No parsing or indexing in this phase.
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
| `statistical_yearbook` | 统计年鉴 | 9 | Official annual statistics and indicator tables |
| `operations` | 作业知识 | 1 | Fishing methods, gear, vessel operations, logbooks and permit conditions |
| `law` | 法律 | 1 | National law adopted by the legislature |
| `regulation` | 行政法规/规章 | 1 | Administrative regulations, departmental rules and implementing provisions |
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

| Source | Type | Document | Status |
|---|---|---|---|
| `POL-LAW-009` | `law` | Fisheries Law, 2025 revision | acquired; **standard text replacement pending** |
| `POL-STD-010` | `regulation` | Fishing permit regulation, 2022 revision | acquired |
| `POL-CLOS-015` | `notice` | Seasonal closure notice, 2023 | acquired |

The Fisheries Law currently comes from a government reprint. It must be replaced with the NPC/gov.cn standard text before it is treated as authoritative.

## 6. Candidate sources

| ID | Type | Title | Priority |
|---|---|---|---|
| `OPS-STAT-001` | `statistical_yearbook` | Generic fisheries statistical yearbook candidate, superseded by the eight editions | P1 |
| `OPS-LOG-002` | `operations` | Logbook and fishing-record specification | P1 |
| `VMS-DICT-003` | `data_dictionary` | Vessel/voyage data dictionary | P2 |
| `VMS-SAMPLE-004` | `data_dictionary` | Desensitised voyage sample description | P2 |
| `ENV-SST-005` | `fishery_product` | Sea surface temperature product description | P2 |
| `ENV-CHL-006` | `fishery_product` | Chlorophyll/current/wind product description | P2 |
| `FCS-BULL-007` | `fishery_product` | Fishing-ground and season bulletin | P2 |
| `FCS-REC-008` | `fishery_product` | Historical fishing-ground and season record | P2 |
| `DICT-STAT-013` | `data_dictionary` | Statistical indicator definitions | P1 |
| `DICT-META-014` | `data_dictionary` | Metadata and data-quality rules | P2 |

Papers and reports were removed from the register because they are not accepted as authoritative project sources at this stage.

## 7. Status summary

| Metric | Value |
|---|---:|
| Corpus types | 8 |
| Registered sources | 21 |
| Acquired sources | 11 |
| Remaining candidates | 10 |
| Yearbook editions | 8 |
| Yearbook data years | 2017–2024 |
| Yearbook files | 838 |
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

- Coastal-port infrastructure is missing for data years 2018 and 2019.
- The vessel-length proxy is missing for data year 2024; the 2025 edition does not include the length table.
- The vessel-length table is a marine production-vessel proxy, not capture-only.
- The published South China Sea column includes Fujian in some data years; the register will store the published value, the Guangdong/Guangxi/Hainan subtotal and the difference.

## 9. Licence and sensitivity policy

| Case | Action |
|---|---|
| `license: unknown` or `sensitivity: unknown` | Hold; do not ingest or index |
| `public` | Policy documents; may be used under the project's normal rules |
| `internal` | Yearbooks; owner-confirmed official/authorized; local use only; no public values |
| `restricted` | Local only; never send to an external model API |
| AIS/VMS sample | Licence and compliance review first; desensitise; keep only necessary fields |
| Personal information | Aggregate or anonymise; never commit or send externally |
| Copyrighted literature | Not registered in the current phase |

## 10. Data and artifact boundary

- Source files, core CSVs and indexes belong in the local data root (`SCS_FKB_DATA_ROOT`), outside the repository.
- Run artifacts belong in the local run root (`SCS_FKB_RUN_ROOT`), outside the repository.
- The public repository contains no data values, indexes, run outputs or state databases.
- Details: [data-policy.md](data-policy.md).

## 11. Gaps and next steps

1. Build the local long-table core indicator CSV from the coverage matrix.
2. Replace the Fisheries Law reprint with the official NPC/gov.cn standard text.
3. Search national and provincial official candidates for the operations, logbook and gear sources; present them before registration.
4. Review the coverage matrix and decide whether the data is sufficient for the next phase.
5. Do not plan or implement the retrieval pipeline until that review is accepted.

## 12. References

- [Corpus register](../configs/corpus.yaml)
- [Statistics schema](../configs/statistics.yaml)
- [Data schema](../configs/schema.yaml)
- [Data policy](data-policy.md)
- [Project plan](plan.md)
- [Project scope](../PROJECT.md)
