# Project Log

This log records material project changes by date. It does not use release versions and is not tied to GitHub Releases.

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
