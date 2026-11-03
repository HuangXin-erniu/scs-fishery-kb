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
