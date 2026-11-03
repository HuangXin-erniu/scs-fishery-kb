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

The seed list [species-seed.yaml](../configs/species-seed.yaml) names 116 South China Sea species across commercial fish, crustaceans, cephalopods, shellfish and protected megafauna. Each name becomes a WoRMS card with a deterministic id (`WEB-WORMS-<NAME>`), and the builder in `knowledge_build.py` turns the returned record into a note with scientific name, authority, classification, marine flags and AphiaID.

| Result | Count |
|---|---|
| Seed species | 116 |
| Cards fetched ok | 115 |
| Cards failed | 1 (`Prionace glauca`, TLS reset) |
| Notes after the batch | **115** (4 pilot + 111 new) |
| Species with a note | 115 |

Protection status and distribution are deliberately not asserted: the WoRMS record does not carry them, so every note says the field is unverified. A failed card produces no note.
