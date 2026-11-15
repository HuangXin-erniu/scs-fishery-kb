# ADR 0013: Source schema v5 (provisional, quality and freshness fields)

> 中文摘要：在 v4 上追加 provisional 入级、许可证证据、解析质量、实用标签与 TTL 字段；只增不改，id/hash 不变，提供 v4→v5 迁移与审计。

- Status: Proposed
- Date: 2026-11-12

## Context

Source schema v4 already records authority tier, level, source class,
provenance, effective dates, quality, currency cadence, licence, sensitivity,
lifecycle and retrieval channel. The second-stage plan adds three things v4
cannot express without overloading a text field:

1. a **provisional** ingestion tier that is visible to the answer path and to
   the metrics;
2. **licence evidence** (the page or terms the operator actually read) and
   **parse quality** scores that a reviewer can compare;
3. **practical** tags (domain, persona, task tags, seasonality) and a
   per-source TTL that the answer path can use for freshness.

## Decision

- Add an additive schema v5 on top of v4. New fields:
  - `authority.score` (0–5) and `authority.evidence_url`;
  - `currency.ttl_days`;
  - `license_evidence {url|text, checked_at}`;
  - `ingest {tier: canonical|provisional, reviewed_by, reviewed_at, review_note}`;
  - `quality.text_coverage`, `quality.anchor_coverage`, `quality.table_count`,
    `quality.ocr_confidence`;
  - `practical {domain, personas, task_tags, seasonal}`;
  - `supersedes`/`superseded_by` as a validated pair.
- The loader accepts v4 records and derives safe defaults; `scripts/migrate_v5.py`
  writes the derivation audit. Ids, hashes, licences and sensitivity are never
  changed by the migration.
- Validation rules:
  - `provisional` may appear in the index but cannot be the sole support for a
    rule, status, quantity or warning;
  - `license_evidence` is required for a canonical practical source;
  - `ttl_days` is positive and consistent with the cadence;
  - `supersedes` and `superseded_by` are symmetric and resolve to registered ids.
- The public repository carries the schema and the migration script; source
  records with payload-level provenance stay local as before.

## Consequences

- The register stays backward compatible; an older v4 file still loads.
- CI gains schema checks for the new fields and the provisional rule; no
  network or model is needed.
- The migration is a one-way audit: it writes a derivation report and never
  rewrites an id or a hash.
- A future v6 is possible; the loader keeps the version field so records can
  coexist during a migration window.

## Alternatives considered

- **Overload existing v4 text fields**: no validation, no queryable semantics;
  rejected.
- **Put provisional/quality metadata in a sidecar file**: avoids a schema bump
  but splits the source record; rejected because the answer path and the CI
  gate need one authority.
- **Break to a new register format**: loses the 106-record history and the
  existing candidates; rejected.

## References

- [Data model](../data-model.md)
- [Sources](../sources.md)
- [RAG standard](../rag-standard.md) section 1
- [Data policy](../data-policy.md)
