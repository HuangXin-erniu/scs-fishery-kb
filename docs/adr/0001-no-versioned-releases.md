# ADR 0001: No versioned releases

- Status: Accepted
- Date: 2026-10-31

## Context

The project is an early-stage public framework. A version line and GitHub Releases
would imply a compatibility promise the project cannot keep, and the repository has
no release artifacts to distribute. Users need a stable way to refer to a state
without a version number.

## Decision

- Do not use semantic versions, Git tags or GitHub Releases.
- `main` is the only supported line; a commit SHA identifies a state.
- Record material changes by date in [the project log](../project-log.md).
- Keep `CITATION.cff` without `version` or `date-released`.
- CI fetches tags and fails when any tag exists; the public-tree check rejects tags.

## Consequences

- Users cite a commit SHA rather than a release number.
- There are no per-release notes; the dated project log is the change record.
- Reintroducing versions requires a new ADR and an explicit owner decision.

## References

- [Project scope](../../PROJECT.md)
- [Public-tree check](../../scripts/check_public_tree.py)
- [CI workflow](../../.github/workflows/ci.yml)
