# Data Model

> **中文摘要**：本文件定义语料登记 schema v2。每条来源必须声明层级（国家/省/市/国际）、权威等级（A/B/C）、来源类别（规范/官方统计/标准/参考）、时效（核验日期、依据、复查日期）、可检索性（通道、可解析）和生命周期（在用/退役）。不再判断"是否现行"；复查日期到期由 watch 提醒，网络卡片另有 30 天周期。退役保留哈希与文件，删除只用于无许可或非官方来源。

## 1. Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | string | yes | Stable source identifier, unique across the register |
| `type` | string | yes | law, regulation, notice, standard, plan, operations, statistical_yearbook, data_dictionary, fishery_product |
| `title`, `title_zh` | string | yes | English and Chinese titles |
| `publisher` | string | yes | Issuing body, not the host that reposted it |
| `year` | integer | yes | Publication year |
| `jurisdiction` | string | yes | national, hainan, guangxi, guangdong, fujian, or the region the document governs |
| `format` | string | yes | html, pdf, ofd, docx, xlsx, xls |
| `location`, `hash` | string | yes | Local path and sha256 of the registered bytes |
| `license`, `sensitivity` | string | yes | Licence and sensitivity marker |
| `status` | string | yes | Acquisition status: acquired, candidate, deferred |
| `level` | enum | yes | `national` / `provincial` / `municipal` / `international` |
| `authority_tier` | enum | yes | `A` publisher's own page, `B` gazette or official attachment or compilation, `C` municipal page |
| `source_class` | enum | yes | `normative` / `official_statistics` / `standard` / `reference` |
| `currency` | mapping | yes | See section 2 |
| `retrieval` | mapping | yes | See section 3 |
| `lifecycle` | enum | yes | `active` / `retired` |
| `retirement` | mapping | when retired | `date`, `reason`, `decision_key` |

## 2. Source class and currency

```yaml
source_class: normative | official_statistics | standard | reference
currency:
  as_of: '2026-11-03'
  basis: publication | edition | announcement | retrieval
  review_due: '2026-12-03'
  note: optional evidence sentence or review remark
```

- `source_class` says what kind of source it is, not whether it is current. `normative` covers laws, regulations and notices; `official_statistics` covers yearbook editions and statistical series; `standard` covers technical standards and operational norms; `reference` covers definitions, product documentation and other reference material.
- `currency.as_of` is the date the entry was last checked; `basis` names what that check rested on; `review_due` is when it must be checked again.
- Default review periods: normative 30 days, standard 90 days, official_statistics one annual edition, reference 180 days; web cards 30 days.
- `currency.note` carries the evidence sentence where one exists (an effective date, an approval number, a publication date) or a short review remark. It is optional, not a status field.
- There is no in-force / not-applicable / unknown state. An entry that cannot be checked keeps its existing dates, and the watch report lists it as due.

## 3. Retrieval

```yaml
retrieval:
  channel: main | collection | statistics | watch | none
  parseable: true | false
  note: one sentence on where the text is reachable
```

- `main` is the frozen legal-and-technical index; `collection` is a reference collection; `statistics` is the extract pipeline; `watch` is monitored but not ingested; `none` means registered for provenance only.
- `parseable: false` marks image-only or otherwise unreachable text. Such a source may stay registered as provenance but must not be cited as if its text were searchable.

## 4. Lifecycle

- `active` sources participate in their channel.
- `retired` sources keep their id, hash and local file, leave every retrieval channel, and carry a `retirement` block with date, reason and decision key. Retirement is for replaced, unparseable or orphaned material; it is not deletion.
- Hard deletion is reserved for sources with no licence and no official provenance. It removes the register entry, the collection entry and the local file, and records the decision that authorised it.

## 5. Admission, supersession and the main index

- Admission: a publisher's own page or an official gazette attachment, a document number or publication date, a licence, and a verified hash.
- Supersession: a newer text supersedes but never deletes; the older entry stays with its date, the newer entry records what it replaces.
- Main index: only `level: national` (or `international`) sources with parseable text and a public or open licence may enter `configs/pipeline.yaml`. Provincial and municipal sources stay in the reference layer.

## 6. Validation

`src/scs_fkb/registry.py` loads the register and enforces the enums, the required mappings, the retirement block and unique ids. CI runs it against the real register, so a malformed entry fails the build rather than reaching an answer.
