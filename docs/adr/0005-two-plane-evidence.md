# ADR 0005: Two-plane evidence

- Status: Accepted
- Date: 2026-11-06

## Context

Answers must be reproducible from a fixed index, citable to a specific document
version and checkable against a recorded hash. A live web fetch would break all
three, bypass the licence check and make the same question return different
evidence on different days. The project nevertheless needs to answer questions
about a policy that changed this week, a closure arrangement announced for this
season or a warning in force now.

## Decision

- **Canonical plane.** Registered sources move through snapshot, parse, chunk,
  index and review. Only this plane can support a primary answer. Each answer
  carries a citation that resolves to a chunk and a source version.
- **Ephemeral plane.** Web search and fetch results are cached as `WebEvidence`
  with URL, publisher, fetched time, content hash, authority tier and TTL. They
  are labelled `网络检索 · 未入知识库` and never enter the canonical index.
- **Promotion is explicit.** A web result may be promoted only by opening a
  candidate, reviewing licence, authority and content, and registering a source.
  There is no automatic ingest path.
- **Conflict is shown, not hidden.** When the canonical and ephemeral planes
  disagree, both statements are displayed with dates and authority. The
  canonical plane wins for law, penalty, statistics and standard questions.

## Consequences

- A web-assisted answer is reproducible only within its TTL; the timestamp and
  hash are part of the citation.
- The query path needs two evidence packs and a clear mode (`kb_only`,
  `kb_plus_web`, `web_only`, `clarify`, `abstain`).
- The register and the web cache need separate lifecycle rules.
- A network failure degrades to a canonical-only answer, never to a fabricated
  one.

## References

- [Sources and authority](../sources.md)
- [Knowledge policy](../knowledge-policy.md)
- [Architecture](../architecture.md)
