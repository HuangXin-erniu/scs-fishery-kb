# ADR 0003: Data and run artifacts outside the repository

- Status: Accepted
- Date: 2026-10-31

## Context

Data payloads, indexes and run artifacts were kept in gitignored `data/` and `runs/`
directories inside the repository. Gitignore is not a security boundary: a forced
add or a misconfigured tool can still publish them.

## Decision

- The local data root and run root live outside the repository, in a sibling
  directory that is not part of the public tree.
- `SCS_FKB_DATA_ROOT` and `SCS_FKB_RUN_ROOT` configure the paths; no absolute path
  is committed.
- The repository contains no `data/` or `runs/` directory.
- [The public-tree check](../../scripts/check_public_tree.py) rejects tracked data
  payloads, run artifacts, caches, binaries and oversized files.

## Consequences

- The public tree has no data surface.
- Local setup requires the two environment variables.
- Migration is a one-time copy plus checksum verification.

## References

- [Data policy](../data-policy.md)
- [Architecture](../architecture.md)
