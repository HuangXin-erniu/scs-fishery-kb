# Project Log

This log records material project changes by date. It does not use release versions and is not tied to GitHub Releases.

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
