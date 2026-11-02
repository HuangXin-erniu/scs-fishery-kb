# Data Model

> **中文摘要**：本文件定义语料登记 schema v2。每条来源必须声明层级（国家/省/市/国际）、权威等级（A/B/C）、现行性（状态、核验日期、前身后继）、可检索性（通道、可解析）和生命周期（在用/退役）。未核验的现行性一律写 unknown，不得默认有效；退役保留哈希与文件，删除只用于无许可或非官方来源。

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
| `validity` | mapping | yes | See section 2 |
| `retrieval` | mapping | yes | See section 3 |
| `lifecycle` | enum | yes | `active` / `retired` |
| `retirement` | mapping | when retired | `date`, `reason`, `decision_key` |

## 2. Validity

```yaml
validity:
  status: in_force | superseded | repealed | unknown
  as_of: '2026-11-02'
  supersedes: [POL-...]        # optional, registered or named predecessors
  superseded_by: [POL-...]     # optional, required when status is superseded
  note: the evidence sentence or the reason the status is unknown
```

Rules:

- `in_force` requires a recorded evidence sentence (a citation by a later official document, an effective date, or the publisher's own current marker).
- `superseded` requires a named successor; otherwise use `unknown` and name the suspected successor in the note.
- `repealed` requires the repealing act.
- `unknown` is the honest default for anything not verified. It is not a placeholder to be left forever: the national entries are re-checked in the currency table.

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
