# Knowledge Policy

> **中文摘要**：本文件规定知识库如何选择、组合和更新证据。问题先按"主张性质"与"知识领域"两级分类；性质决定哪些证据可作主证据、需要多新的证据；领域细化来源类别。回答由主证据支撑，外部条目只能作辅证；冲突并列标注；过期证据不得用于现状类主张。内化由拒答、watch 变化、季度复查和引用计数四类触发驱动。

## 1. Two-level taxonomy

| Nature | What it claims | Window | Primary evidence |
|---|---|---|---|
| definition | what something is | none | authoritative or standard; normative/standard/reference; corpus/note/web |
| rule | what must be done or submitted | 30 days | authoritative; normative/standard; corpus/note |
| quantity | how much or which trend | 1 year | authoritative; official_statistics/normative; corpus/note |
| status | what is currently in force | 30 days | authoritative; normative/official_statistics; corpus/note |
| warning | what is coming or in force now | 7 days | authoritative or standard; normative/reference; note/web |
| identification | which species or attribute | 90 days | authoritative or standard; reference/standard; note/web/corpus |
| history | how it changed | none | authoritative or standard; normative/reference; corpus/note |

Domains: policy, gear, environment, hazard, species, statistics, port. The nature decides admissibility; the domain refines source classes. Unknown questions fall back to `general`, which permits corpus evidence only.

## 2. Trust tiers

| Tier | Rule |
|---|---|
| `authoritative` | normative or official-statistics text; or two independent A-tier sources agreeing |
| `standard` | A-tier source reviewed once by the operator |
| `provisional` | single source, unreviewed, B/C tier or low confidence |

`authoritative` may be primary for any nature. `standard` may be primary only for definition, identification and history. `provisional` is supporting evidence only.

## 3. Combining corpus and external knowledge

- **Primary evidence** must be admissible for the nature, fresh within the window, and at an allowed trust tier. The answer's core claim rests on it.
- **Supporting evidence** may add definitions, scope or background. It must not introduce a new claim. Citations are labelled `[primary]` or `[supporting]`.
- **Conflict**: when primary and supporting evidence disagree, both statements are shown with a conflict marker; the system never silently picks one.
- **Expired evidence** may only be used in a historical statement, never as current status, quantity or warning.

## 4. Internalisation triggers

1. A refusal or follow-up question is recorded as a knowledge gap and seeds the next card/note batch.
2. A watch change marks the affected notes stale and queues a review.
3. The quarterly review (2027-02-02) re-dates every entry and retires what is no longer supported.
4. Citation counts promote frequently used notes for review and tier upgrade (provisional → standard → authoritative).

## 5. Configuration

The machine-readable matrix is [configs/claims.yaml](../configs/claims.yaml); the classifier is `src/scs_fkb/claims.py`. The matrix is reviewed with every quarterly sweep, and a change to a window or trust rule is a decision recorded in the project log.

## 6. Two-index architecture

The corpus store (28 documents, index `20910f0964df`) and the external store (`$SCS_FKB_DATA_ROOT/external`, 259 documents and 315 chunks: 119 cards plus 140 notes) are built and embedded separately. Answering always starts from the corpus index: abstention is decided there and nowhere else. Only when the corpus answer is not an abstention does `ask` query the external index and append labelled supporting evidence (`外部知识（辅助，不改变主结论）`). External evidence therefore cannot make an out-of-scope question answerable, and the corpus metrics are unchanged by construction.

Build and refresh:

```bash
scs-fkb ingest                      # corpus store
scs-fkb ingest --external-only --data-root "$SCS_FKB_DATA_ROOT/external"
scs-fkb embed --data-root "$SCS_FKB_DATA_ROOT/external"
```

## 7. Knowledge gaps

Every refusal is written to `$SCS_FKB_DATA_ROOT/gaps.jsonl` with the timestamp, question, refusal reason, claim nature and domain. `scs-fkb knowledge gaps` groups the file by nature, domain and reason and prints the most recent questions; the largest clusters become the next acquisition targets. Logging never changes or delays an answer; a write failure is ignored.

## 8. Quarterly review

The real sweep is scheduled for **2027-02-02**. The procedure is: `knowledge check --write` (marks changed or expired notes stale), `watch --offline` (lists due register entries and cards), review every `draft` and `stale` note, update `review_due`, and record the outcome in the project log.

A preview run on 2026-11-03 reported **0 stale, 0 due** notes and **26 ok** watch entries; nothing is due before December 2026, so the preview is recorded as a rehearsal, not as the scheduled sweep.
