# Knowledge Notes

> **中文摘要**：本文件定义"知识条目"层。条目把卡片或语料中的事实提炼为带标签的结构化字段，注明海区、核验日期、复查日期、状态与来源（卡片或语料文档，绑定 SHA-256）。条目由 `scs-fkb knowledge` 校验；官方 A 级来源可自动 approved，其余先 draft 人工确认；来源哈希变化或灾害条目过期即标 stale，停止使用。

## 1. Schema

```yaml
schema_version: 1
topic: species
notes:
  - id: KNO-SPECIES-001
    title: 大黄鱼 Larimichthys crocea
    summary: 南海近岸重要经济鱼种；WoRMS 分类记录。
    facts:
      - {label: 学名, value: Larimichthys crocea}
      - {label: 分类, value: Chordata > Teleostei > ... > Sciaenidae}
    sea_area: 南海
    species: [Larimichthys crocea]
    as_of: '2026-11-03'
    review_due: '2027-02-01'
    status: approved            # draft | approved | stale | retired
    confidence: high
    sources:
      - {card: WEB-WORMS-..., sha256: ..., url: ..., fetched_at: '2026-11-03'}
```

Rules:

- `facts` is a non-empty list of `{label, value}` pairs; each fact must be supported by a cited source.
- `sources` is a non-empty list; a card source pins the card's `sha256`, a document source pins the corpus hash.
- `review_due` must not precede `as_of`; a past review date marks the note **due**, not stale.
- A changed card hash or an expired `expires_at` (hazard notes) marks the note **stale**; stale notes are not approved and will not be indexed.
- Only A-tier official sources may be auto-approved; everything else starts as `draft` and needs `scs-fkb knowledge approve <id>`.
- Topics: `species`, `policy`, `gear`, `environment`, `hazard`, `stats`.

## 2. Commands

| Command | Purpose |
|---|---|
| `scs-fkb knowledge list` | List notes with topic, status and review date |
| `scs-fkb knowledge check --write` | Validate, mark changed/expired notes stale, report due notes |
| `scs-fkb knowledge approve <id>` | Approve a draft note (refused if stale) |

## 2a. Playbooks (2026-11-06)

A playbook is a short, persona-specific procedure. Every step cites at least one
approved fact; the validator rejects an unknown, draft or stale fact and a source
that is not in the register. The first batch has 15 playbooks and 32 steps:

| Playbook | Persona | Covers |
|---|---|---|
| PLAY-CAPTAIN-001 | captain | Closure compliance |
| PLAY-OWNER-002 | owner | Special-permit application |
| PLAY-OWNER-003 | owner | Marine permit application |
| PLAY-OWNER-004 | owner | Permit renewal and annual review |
| PLAY-OWNER-005 | owner | Vessel/gear quota |
| PLAY-CAPTAIN-006 | captain | Logbook |
| PLAY-CAPTAIN-007 | captain | Port entry and reporting |
| PLAY-OWNER-008 | owner | Vessel inspection |
| PLAY-OWNER-009 | owner | Resource fee |
| PLAY-CAPTAIN-010 | captain | Minimum mesh and gear check |
| PLAY-EXTENSION-011 | extension | Gear classification |
| PLAY-CAPTAIN-012 | captain | Penalty response |
| PLAY-CAPTAIN-013 | captain | Port berthing and safety check |
| PLAY-EXTENSION-014 | extension | Capture statistics definitions |
| PLAY-CAPTAIN-015 | captain | Fisheries Law duties |

The playbook layer is validated by `scripts/check_playbooks.py`; the weekly
script runs it together with the fact and term checks. A playbook is not a
substitute for the source text: it always links the underlying provision.

## 3. Pilot (2026-11-03)

| Note | Topic | Facts | Source |
|---|---|---|---|
| KNO-SPECIES-001 | species | 大黄鱼 taxonomy | WoRMS card |
| KNO-SPECIES-002 | species | 带鱼 taxonomy | WoRMS card |
| KNO-SPECIES-003 | species | 蓝圆鲹 taxonomy | WoRMS card |
| KNO-SPECIES-004 | species | 中国明对虾 taxonomy | WoRMS card |
| KNO-POLICY-001 | policy | 南海休渔海域、时间、小型张网 | POL-CLOS-015 |
| KNO-POLICY-002 | policy | 捕捞许可证申请材料 | POL-STD-010 第二十八条 |
| KNO-POLICY-003 | policy | 2026 专项捕捞品种 | POL-SPEC-041 |
| KNO-GEAR-001 | gear | FAO 捕捞数据采集指南 | FAO card |
| KNO-ENV-001 | environment | Sentinel-3 轨道与海洋变量 | EUMETSAT card |
| KNO-HAZARD-001 | hazard | 预警信号分级、种类、发布主体 | gov.cn 预警办法 |

## 4. Species scale batch (2026-11-03)

The seed list species-seed.yaml（已移除） names 116 South China Sea species across commercial fish, crustaceans, cephalopods, shellfish and protected megafauna. Each name becomes a WoRMS card with a deterministic id (`WEB-WORMS-<NAME>`), and the builder in `knowledge_build.py` turns the returned record into a note with scientific name, authority, classification, marine flags and AphiaID.

| Result | Count |
|---|---|
| Seed species | 116 |
| Cards fetched ok | 115 |
| Cards failed | 1 (`Prionace glauca`, TLS reset) |
| Notes after the batch | **115** (4 pilot + 111 new) |
| Species with a note | 115 |

Protection status and distribution are deliberately not asserted: the WoRMS record does not carry them, so every note says the field is unverified. A failed card produces no note.

## 5. Topic coverage (2026-11-03)

| Topic | Notes | Source base |
|---|---|---|
| species | 115 | WoRMS cards |
| policy | 10 | corpus documents (closures, permits, crew, ports, penalties, VMS, e-certificates) |
| gear | 6 | mesh standards, GB/T 5147—2026, SC/T 9460—2025, FAO guide, closure operation types |
| environment | 2 | EUMETSAT Sentinel-3, NASA Ocean Biology DAAC |
| hazard | 4 | gov.cn warning-signal measures |
| stats | 3 | output definition, fishery yearbook, statistical yearbook |
| **total** | **140** | |

Every note pins at least one source with a SHA-256. Facts that the source does not state — protection status, prices, exact values — are left out, and a card that fails to fetch produces no note.

## 6. Index status (2026-11-03)

The layer is complete and validated, and it is indexed **as a separate external store** (259 documents, 315 chunks: 119 cards and 140 notes, index `0c6d3901106c`), not in the corpus index. This section records the note-only build; the current store after P09-KB-131 is in section 7.4. Two rebuilds of the single index were measured: with cards and notes the index reached 287 documents and hybrid fell to 9/11 with abstention 2/4; with cards only it reached 147 documents and hybrid held at 11/11 but abstention fell to 2/4. Broad external evidence without an abstention-aware gate removes correct refusals, so the corpus-only twenty-eight-document baseline stays in force. A layered gate (corpus evidence required before cards or notes can support an answer) was implemented and measured: BM25 abstention recovered to 3/4 but hybrid stayed at 2/4 with recall 9/11, so the notes still wait. A claim-matrix filter (nature, trust, kind, freshness) was wired in and measured: BM25 abstention stayed at 3/4 but hybrid remained 9/11 with abstention 2/4, because the enlarged dense pool changes corpus ranking itself; the fix is structural: the corpus store and the external store are now separate, and the external store (cards and notes) is only consulted after a non-abstained corpus answer, and refusals are logged to `gaps.jsonl`, summarised by `scs-fkb knowledge gaps` (see knowledge-policy.md §6 to §8). The corpus index stays at 28 documents, 785 chunks and `20910f0964df`; the external store never decides abstention.

## 7. Fact, term and FAQ layer (2026-11-04)

The note layer is descriptive; P09-KB-131 adds a verified fact layer and two support layers. All three live outside the corpus index and are indexed only in the external store.

### 7.1 Facts

```yaml
- id: FACT-POLICY-001
  kind: atomic            # atomic | provision
  topic: policy
  question_class: time_range
  subject: 南海区伏季休渔
  predicate: 休渔时间
  value: 5月1日12时至8月16日12时（北纬26度30分至北纬12度）
  unit: null
  qualifiers: {area: 北纬26度30分至北纬12度}
  jurisdiction: national
  effective: {from: '2023-04-15', to: null}
  evidence: 北纬26度30分至北纬12度的东海和南海海域为5月1日12时至8月16日12时
  source: {doc: POL-CLOS-015, section: 三、休渔时间, sha256: ...}
  status: approved
  confidence: high
  as_of: '2026-11-04'
  review_due: '2026-12-03'
  supersedes: null
```

The layer has **200 facts**: 100 approved and 100 draft provision facts. The approved set has 20 atomic facts with precise values/units/effective dates and 80 provision facts that tag an article or section with a `question_class`, `subject` and `predicate`. The 2026-11-06 review promoted 20 of the 120 generated provision facts; the remaining 100 stay draft. Every fact carries a verbatim `evidence` quote and a `source` with the register hash.

`scs-fkb facts check --data-root "$SCS_FKB_DATA_ROOT"` verifies that the evidence is a substring of a chunk with the same document and section, that the source hash equals the register, that approved facts use an A/B public source, that effective dates do not invert, and that facts with the same subject/predicate/jurisdiction do not overlap with different values. A `supersedes` chain resolves an intentional replacement. The check exits non-zero on any error, conflict or expired fact; facts approaching `review_due` are reported as due.

### 7.2 Terms

```yaml
- id: TERM-001
  standard: 渔业捕捞许可证
  variants: [捕捞证, 捕鱼证, 牌照]
  region: [national]
  source: {kind: corpus, doc: POL-STD-010, section: 第二条, note: 法定捕捞许可证书}
  status: approved
```

**150 terms** map colloquial wording to the standard term (136 approved, 14 draft). `scs-fkb terms check --data-root ...` requires an approved standard term to appear in the indexed corpus and the corpus source to resolve. The 34 draft terms were reviewed on 2026-11-06; 17 were promoted across three source batches and 3 more in batch 4, so 14 remain draft because their standard forms still do not occur in the registered corpus. Terms are retrieval and answer-wording aids; they never replace a citation.

### 7.3 FAQ

```yaml
- id: FAQ-CAPTAIN-001
  question: 休渔期是什么时候？
  persona: captain
  claims: [FACT-POLICY-001]
  source: {kind: public, note: corpus facts; no eval or real-user question}
  status: approved
```

**12 public FAQs** cover the four personas. Every claim resolves to an approved fact; approved FAQs cannot claim a draft fact. No eval question, gold answer or real-user question is used.

### 7.4 Build

```bash
scs-fkb facts check --data-root "$SCS_FKB_DATA_ROOT"
scs-fkb terms check --data-root "$SCS_FKB_DATA_ROOT"
scs-fkb faq check
scs-fkb ingest --external-only --data-root "$SCS_FKB_DATA_ROOT/external"
scs-fkb embed --data-root "$SCS_FKB_DATA_ROOT/external"
```

The rebuilt external store now has **507 documents and 563 chunks** (119 cards, 140 notes, 100 approved facts, 136 approved terms, 12 FAQs), chunk index `458aad366fe1` and dense index `91e8ec609611dccb`. The pre-review store was 375 documents / 431 chunks / `3259a7694499`; the corpus store is now 42 documents, 1014 chunks and `f7a244373e77`.
