# ADR 0007: Controlled web retrieval

- Status: Accepted
- Date: 2026-11-06

## Context

The watch list and cached web cards cover discovery and monitoring, but the
answer path never reads the live web. That keeps answers reproducible and
licence-safe, but it cannot answer questions about a notice published this week,
the current season's closure arrangement or a warning in force now. A general
web search would remove the authority and licence controls that the register
exists to enforce.

## Decision

- Run **SearXNG locally** and query it through its JSON API. No commercial search
  key is required for the base path; a paid adapter may be added later.
- Restrict every query and result to the allowlist in `configs/web-sources.yaml`.
  Discard non-allowlisted domains and record the reason.
- Fetch only `https` pages, cap bytes and timeout, extract the main text with
  `trafilatura`, and store a `WebEvidence` record with URL, publisher, fetched
  time, content hash, authority tier and TTL.
- Trigger web retrieval only when the user asks for it, the question carries a
  freshness cue, the canonical answer abstains inside a supported domain, or the
  canonical evidence is older than the freshness window for that claim nature.
- Label every web-assisted answer `网络检索 · 未入知识库`; cite URL and fetch
  date; never let web evidence override canonical law, penalty or statistics.
- Promote a web result only through the candidate queue and a human review. No
  automatic ingest, no background write to the register or index.

## Consequences

- The web channel is a separate evidence pack and a separate mode; it does not
  change the canonical retrieval metrics by construction.
- A network failure returns the canonical answer with a note that live checking
  was unavailable.
- Web content is untrusted data: it is delimited in the prompt, never executed
  as an instruction, and never copied into the public tree in full.
- The TTL makes the freshness claim explicit and expires stale evidence.

## References

- [Sources and authority](../sources.md)
- [Knowledge policy](../knowledge-policy.md)
- [SearXNG documentation](https://docs.searxng.org/)
- [trafilatura](https://github.com/adbar/trafilatura)
