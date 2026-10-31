# ADR 0004: Public/private boundary

- Status: Accepted
- Date: 2026-10-31

## Context

The project is developed inside a private research programme. Internal names, task
identifiers, local paths and private data must not reach the public repository.

## Decision

- The public tree contains only documentation, configuration, scripts and tests.
- Forbidden in the public tree: internal programme names, task identifiers,
  absolute local paths, private project identifiers, credentials, data payloads,
  indexes, run artifacts and state databases.
- Two gates run before every push: the public-tree check in the repository and the
  private release gate outside it.
- GitHub secret scanning and push protection stay enabled.
- Contributors must not paste restricted material into issues, discussions or
  pull requests.

## Consequences

- A push is blocked when either gate fails.
- The private gate stays outside the repository and is never published.

## References

- [Data policy](../data-policy.md)
- [Security policy](../../.github/SECURITY.md)
- [Contributing](../../.github/CONTRIBUTING.md)
- [Style guide](../style-guide.md)
