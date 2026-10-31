# Governance

This document describes who decides what, how changes are reviewed, and which
policies are not negotiable. It is intentionally short.

## Roles

| Role | Responsibility |
|---|---|
| Project owner | Scope, priorities, data classes, external dependencies, publication and final acceptance. |
| Maintainers | Implementation, tests, documentation, review and repository operations. |
| Contributors | Documentation, configuration, tests and code changes within the agreed scope. |
| Domain experts | Question set, terminology, definitions and answer review. |
| Data owners | Source access, licence, sensitivity and permitted use. |

The project owner is the decision authority. Maintainers may merge routine
documentation, configuration, test and tooling changes that pass CI.

## Decisions

- Scope changes, new data classes, new external dependencies, public/private
  boundary changes and governance changes require an owner decision.
- Record material decisions in [docs/adr/](docs/adr/README.md) or in the
  [project log](docs/project-log.md).
- Routine changes go through a pull request or a maintainer commit; CI must pass.
- Security-sensitive reports follow [SECURITY.md](.github/SECURITY.md), not a public issue.

## Versioning and releases

- The project has no semantic versions, Git tags or GitHub Releases; `main` is the
  supported line. The decision and its consequences are recorded in
  [ADR 0001](docs/adr/0001-no-versioned-releases.md).
- Cite a commit SHA when referring to a specific state.
- Do not create version branches, release notes or changelog versions.

## Data and security boundary

- The public repository contains no data payloads, indexes, run artifacts, state
  databases or credentials. Local data and run roots live outside the repository;
  see [ADR 0003](docs/adr/0003-data-outside-repository.md).
- Internal programme names, task identifiers and absolute local paths must not
  appear in the public tree; see [ADR 0004](docs/adr/0004-public-private-boundary.md).
- Data handling rules are in [docs/data-policy.md](docs/data-policy.md).

## Changes to this document

Open a pull request that explains the change and its consequences. The project
owner approves governance changes; record the outcome in the project log.
