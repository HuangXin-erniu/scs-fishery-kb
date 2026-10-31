# Corpus Inventory

- Status: three P1 policy documents acquired; twelve candidates remain.
- Register: [configs/corpus.yaml](../configs/corpus.yaml)
- Date: 2026-10-31

## 1. Purpose and scope

This inventory covers the **knowledge layer** of the project: fishing-vessel operations and catch statistics, vessel/voyage data dictionaries and desensitised sample descriptions, ocean and fishery product descriptions, fishery bulletins and historical season records, laws and standards, papers and reports, and data dictionaries.

It does **not** include raw environmental grids, reanalysis data, forecast rasters or products, full AIS/VMS tracks, or unlicensed material. Those are outside the knowledge-layer scope. No data payload is published in this repository.

## 2. Method

1. Define seven knowledge categories and at least two candidate sources per category.
2. Register each candidate with title, publisher, year, type, format, location, licence, sensitivity, status, priority, volume, update frequency, hash and acquisition notes.
3. Mark every unacquired source as `status: to_acquire`, `location: null`, `hash: null`.
4. Hold every source whose licence or sensitivity is `unknown`; do not ingest it.
5. Acquire only from official public channels; record the URL, retrieval date and SHA-256. Do not parse or index a source during inventory.

## 3. Categories

| Category | Candidates | Description |
|---|---:|---|
| Fishing vessel operations and catch statistics (渔船作业与渔获统计) | 2 | Statistical yearbooks, logbook specifications, operation types and catch indicators |
| Vessel/voyage data dictionaries and sample descriptions (船位/航次数据字典与样本说明) | 2 | Field definitions, voyage definitions and desensitised samples; no full tracks |
| Ocean and fishery product descriptions (海洋环境与渔情产品说明) | 2 | SST, chlorophyll, currents and wind: variables, units, resolution and metadata |
| Fishing-ground and season bulletins (渔场/渔汛预报与通报) | 2 | Public bulletins and historical season records; no forecast model outputs |
| Laws, regulations, norms and standards (政策法规、作业规范与标准) | 3 | Fisheries law, seasonal closures, access conditions and gear standards |
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
| POL-LAW-009 | policy_standards | Fisheries Law, 2025 revision (中华人民共和国渔业法) | P1 | acquired |
| POL-STD-010 | policy_standards | Fishing permit regulation, 2022 revision (渔业捕捞许可管理规定) | P1 | acquired |
| POL-CLOS-015 | policy_standards | Seasonal closure notice, 2023 (农业农村部关于调整海洋伏季休渔制度的通告) | P1 | acquired |
| LIT-PAPER-011 | papers_reports | Journal papers on nearshore fisheries (南海近海渔业论文) | P2 | to_acquire |
| LIT-RPT-012 | papers_reports | Project and technical reports (项目/技术报告) | P2 | to_acquire |
| DICT-STAT-013 | data_dictionary | Statistical indicator definitions (统计指标口径) | P1 | to_acquire |
| DICT-META-014 | data_dictionary | Metadata and data-quality rules (元数据/数据质量规范) | P2 | to_acquire |

## 5. Status summary

| Metric | Value |
|---|---:|
| Knowledge categories | 7 |
| Candidate sources | 15 |
| Unique source IDs | 15 |
| Candidates per category | 2 (policy_standards: 3) |
| P1 candidates | 6 |
| P2 candidates | 9 |
| Acquired files | 3 |
| Ingestible sources | 3 |
| `license`/`sensitivity` unknown | 12 |

Three acquired documents are public and ready for parsing. The remaining twelve candidates are held until their licence and sensitivity are confirmed and their file hash is recorded.

## 6. Acquisition priorities

### P1 — first

Acquired:

1. **Fisheries Law (2025 revision)**: the current legal basis, including resource protection, fishing permits and legal liability. Effective 2026-05-01.
2. **Seasonal closure notice (2023)**: the current marine seasonal-closure system, including the South China Sea area and dates.
3. **Fishing permit regulation (2022 revision)**: access conditions, permit fields and vessel-management rules.

Still to acquire:

- **Statistical yearbook and definitions**: production, landed weight, fishing effort and operation-type definitions.
- **Logbook specification**: required fields, reporting process and a desensitised sample.
- **Gear and operational standards**: current gear specifications and operational norms.

The three acquired documents are the best first corpus: official, public, citable and limited in size. The remaining P1 sources are needed before the corpus can answer statistical and logbook questions.

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

- Source files, processed chunks and indexes belong in the local data root (`SCS_FKB_DATA_ROOT`), outside the repository.
- Run artifacts belong in the local run root (`SCS_FKB_RUN_ROOT`), outside the repository.
- The public repository contains no data payloads, indexes, run outputs or state databases.
- Details: [data-policy.md](data-policy.md).

## 9. Gaps and risks

- **Three policy documents acquired**: the corpus can answer legal, closure and permit questions, but not statistical or logbook questions yet.
- **Publishers unknown**: most remaining candidates still need an owner or a confirmed source.
- **Licences uncertain**: statistical yearbooks, internal reports and paper full texts need case-by-case confirmation.
- **Definitions may differ** by region, year and source; expert confirmation is required.
- **Scanned documents and complex tables** may fail extraction; text-layer PDFs come first, low-quality items are quarantined.
- **Acquired HTML needs extraction**: the permit page uses malformed paragraph tags, so the parser must isolate the main content and preserve article anchors.
- **Evaluation questions are drafts**: they need business-expert review before being treated as a gold set.

## 10. Next steps

1. Parse and index the three acquired documents; keep page or article anchors and a reproducible manifest.
2. Acquire the statistical yearbook, logbook specification and gear standards next.
3. Build the minimal ingestion and retrieval pipeline on the acquired documents.
4. Convert confirmed questions into the evaluation set with gold answers and evidence pages.
5. Define the downstream interface contract in a later milestone; do not implement data integration.

## 11. References

- [Corpus register](../configs/corpus.yaml)
- [Data schema](../configs/schema.yaml)
- [Evaluation questions](questions.md)
- [Data policy](data-policy.md)
- [Project scope](../PROJECT.md)
