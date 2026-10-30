# Corpus Inventory

- Status: candidate register complete; **no source files acquired yet**.
- Register: [configs/corpus.yaml](../configs/corpus.yaml)
- Date: 2026-10-30

## 1. Purpose and scope

This inventory covers the **knowledge layer** of the project: fishing-vessel operations and catch statistics, vessel/voyage data dictionaries and desensitised sample descriptions, ocean and fishery product descriptions, fishery bulletins and historical season records, laws and standards, papers and reports, and data dictionaries.

It does **not** include raw environmental grids, reanalysis data, forecast rasters or products, full AIS/VMS tracks, or unlicensed material. Those are outside the knowledge-layer scope. No data payload is published in this repository.

## 2. Method

1. Define seven knowledge categories and at least two candidate sources per category.
2. Register each candidate with title, publisher, year, type, format, location, licence, sensitivity, status, priority, volume, update frequency, hash and acquisition notes.
3. Mark every unacquired source as `status: to_acquire`, `location: null`, `hash: null`.
4. Hold every source whose licence or sensitivity is `unknown`; do not ingest it.
5. Do not download, ingest or fabricate a source during inventory. This document only records candidates and acquisition paths.

## 3. Categories

| Category | Candidates | Description |
|---|---:|---|
| Fishing vessel operations and catch statistics (渔船作业与渔获统计) | 2 | Statistical yearbooks, logbook specifications, operation types and catch indicators |
| Vessel/voyage data dictionaries and sample descriptions (船位/航次数据字典与样本说明) | 2 | Field definitions, voyage definitions and desensitised samples; no full tracks |
| Ocean and fishery product descriptions (海洋环境与渔情产品说明) | 2 | SST, chlorophyll, currents and wind: variables, units, resolution and metadata |
| Fishing-ground and season bulletins (渔场/渔汛预报与通报) | 2 | Public bulletins and historical season records; no forecast model outputs |
| Laws, regulations, norms and standards (政策法规、作业规范与标准) | 2 | Fisheries law, seasonal closures, access conditions and gear standards |
| Papers, reports and monographs (论文、报告、专著) | 2 | Public literature and technical reports that can be used lawfully |
| Data dictionaries and statistical definitions (数据字典与统计口径) | 2 | Indicator definitions, metadata and data-quality rules |

## 4. Candidates

| ID | Category | Title | Priority | Status |
|---|---|---|---|---|
| OPS-STAT-001 | fishery_operations | Fisheries statistical yearbook (渔业统计年报) | P1 | to_acquire |
| OPS-LOG-002 | fishery_operations | Logbook and fishing-record specification (捕捞日志规范) | P1 | to_acquire |
| VMS-DICT-003 | vessel_tracks | Vessel/voyage data dictionary (船位/航次数据字典) | P2 | to_acquire |
| VMS-SAMPLE-004 | vessel_tracks | Desensitised voyage sample description (脱敏航次样本说明) | P2 | to_acquire |
| ENV-SST-005 | ocean_fishery_products | Sea surface temperature product description (SST 产品说明) | P2 | to_acquire |
| ENV-CHL-006 | ocean_fishery_products | Chlorophyll/current/wind product description (叶绿素/海流/风场产品说明) | P2 | to_acquire |
| FCS-BULL-007 | forecast_bulletins | Fishing-ground and season bulletin (渔场/渔汛通报) | P2 | to_acquire |
| FCS-REC-008 | forecast_bulletins | Historical fishing-ground and season record (历史渔汛记录) | P2 | to_acquire |
| POL-LAW-009 | policy_standards | Fisheries law and seasonal-closure regulations (渔业法/伏季休渔法规) | P1 | to_acquire |
| POL-STD-010 | policy_standards | Operational norms, access conditions and gear standards (作业规范/渔具标准) | P1 | to_acquire |
| LIT-PAPER-011 | papers_reports | Journal papers on nearshore fisheries (南海近海渔业论文) | P2 | to_acquire |
| LIT-RPT-012 | papers_reports | Project and technical reports (项目/技术报告) | P2 | to_acquire |
| DICT-STAT-013 | data_dictionary | Statistical indicator definitions (统计指标口径) | P1 | to_acquire |
| DICT-META-014 | data_dictionary | Metadata and data-quality rules (元数据/数据质量规范) | P2 | to_acquire |

## 5. Status summary

| Metric | Value |
|---|---:|
| Knowledge categories | 7 |
| Candidate sources | 14 |
| Unique source IDs | 14 |
| Candidates per category | 2 |
| P1 candidates | 5 |
| P2 candidates | 9 |
| Acquired files | 0 |
| Ingestible sources | 0 |
| `license`/`sensitivity` unknown | 14 |

No source can be ingested until its licence and sensitivity are confirmed and its file hash is recorded.

## 6. Acquisition priorities

### P1 — first

1. **Laws and standards**: fisheries law, seasonal closures, vessel management, operational norms and gear standards. Obtain current effective versions from official public channels.
2. **Statistical yearbook and definitions**: production, landed weight, fishing effort and operation-type definitions.
3. **Logbook specification**: required fields, reporting process and a desensitised sample.

These five candidates are the best first corpus: they are relatively public, highly citable and limited in size.

### P2 — second

- Vessel/voyage data dictionaries and desensitised sample descriptions.
- SST, chlorophyll, current and wind product descriptions and metadata.
- Public fishery bulletins and historical season records.
- Public papers, project reports and technical reports.
- Metadata and data-quality rules.

For P2, confirm copyright, internal-report status or sample restrictions before ingestion.

## 7. Licence and sensitivity policy

| Case | Action |
|---|---|
| `license: unknown` or `sensitivity: unknown` | Hold; do not ingest or index |
| `public` | May be ingested; external model use depends on `SENSITIVITY_CEILING` |
| `internal` | Owner approval required; desensitise before external use |
| `restricted` | Local only; never send to an external model API |
| AIS/VMS sample | Licence and compliance review first; desensitise; keep only necessary fields |
| Personal information | Aggregate or anonymise; never commit or send externally |
| Copyrighted literature | Only permitted full text or abstracts; no bulk scraping |

## 8. Data and artifact boundary

- Source files, processed chunks and indexes belong in the local `data/` directory, which is gitignored except for `data/README.md`.
- Run artifacts belong in the local `runs/` directory, which is gitignored entirely.
- The public repository contains no data payloads, indexes, run outputs or state databases.
- Details: [data-policy.md](data-policy.md).

## 9. Gaps and risks

- **No acquired files**: the first ingestion milestone needs two or three public documents with clear licences.
- **Publishers unknown**: most candidates still need an owner or a confirmed source.
- **Licences uncertain**: statistical yearbooks, internal reports and paper full texts need case-by-case confirmation.
- **Definitions may differ** by region, year and source; expert confirmation is required.
- **Scanned documents and complex tables** may fail extraction; text-layer PDFs come first, low-quality items are quarantined.
- **Evaluation questions are drafts**: they need business-expert review before being treated as a gold set.

## 10. Next steps

1. Confirm and obtain two or three P1 public documents (laws, standards or statistical definitions first).
2. Record licence, sensitivity, version and hash for each acquired file in the register.
3. Build the minimal ingestion and retrieval pipeline on those documents.
4. Convert confirmed questions into the evaluation set with gold answers and evidence pages.
5. Define the downstream interface contract in a later milestone; do not implement data integration.

## 11. References

- [Corpus register](../configs/corpus.yaml)
- [Data schema](../configs/schema.yaml)
- [Evaluation questions](questions.md)
- [Data policy](data-policy.md)
- [Project scope](../PROJECT.md)
