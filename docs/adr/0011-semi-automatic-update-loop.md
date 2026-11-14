# ADR 0011: Semi-automatic update loop with a provisional tier

> 中文摘要：把八步手工更新改成“定时发现→规则门禁→临时入库→人工抽检转正”；A 级官方源也不自动转正，临时来源不得单独支撑强主张。

- Status: Proposed
- Date: 2026-11-12

## Context

The weekly cycle is read-only: watch, report, candidate draft, then a human
reads the page and a second human workflow captures, registers, rebuilds,
regresses and records. There is no scheduler, no content diff and no automatic
promotion, and the gap queue is nearly empty because the query log is off by
default. The corpus therefore cannot keep up with changed notices, new
standards or seasonal bulletins.

## Decision

- Add a scheduled **semi-automatic** cycle (`scripts/update_cycle.py`):
  1. run the existing hard gates (currency, candidates, watch coverage);
  2. poll only due sources with a rate limit and a recorded user agent;
  3. diff the snapshot by content hash;
  4. apply quality gates: parse coverage, anchors, table integrity, duplicate
     detection, licence and sensitivity;
  5. capture and index the changed pages into a **provisional** tier;
  6. write candidate records and a promotion draft;
  7. run a fixed smoke set (retrieval + citation);
  8. write a dated report and the next actions.
- **Provisional semantics**: `ingest.tier=provisional`, `trust=provisional`.
  Provisional evidence may be shown with an explicit "临时来源·待复核" label,
  but it cannot alone support a rule, status, quantity or warning, and it is
  excluded from the canonical Track A/Track B metrics.
- **Human review is the promotion gate**: a reviewer inspects the page, the
  licence and the quality block, then promotes to `canonical` or rejects. No
  automatic canonical promotion, including for tier-A official pages.
- The scheduler is a macOS launchd user agent (weekly full run, daily for
  daily-cadence sources); a lock file prevents overlap and every run writes to
  the local run root. A failed run leaves the previous index in place.
- The downgrade path is explicit: the index pointer keeps the previous version,
  the register keeps the previous entry, and a rejected candidate stays open or
  is marked rejected with a note.

## Consequences

- The update loop becomes continuous without turning the knowledge base into a
  live web fetch: canonical answers still come from a fixed, hashed index.
- Review capacity becomes the bottleneck; the promotion queue, SLA and sample
  rate are operational parameters, not code constants.
- Provisional content can leak into an answer if the label is ignored. The
  answer path and the UI must both show the label; tests enforce the
  "cannot be sole support" rule.
- The cycle needs offline-safe behaviour: if the network fails, it records the
  failure and keeps serving the previous index.

## Alternatives considered

- **Full automatic promotion**: fastest, but a changed page, a repost or a
  licence change would enter the canonical index without review; rejected.
- **Keep the manual cycle**: safest, but the user explicitly asked for
  continuous updating; rejected.
- **Live web fetch at answer time as the update mechanism**: breaks
  reproducibility, citation and licence checks; rejected (see ADR 0005).

## References

- [Operations](../operations.md)
- [Sources](../sources.md)
- [RAG standard](../rag-standard.md) sections 7 and 9
