# Data Model

> **中文摘要**：本文件定义语料登记 schema v3。每条来源必须声明层级（国家/省/市/国际）、权威等级（A/B/C）、来源类别（规范/官方统计/标准/参考）、时效（核验日期、依据、复查日期、复查节奏）、许可与敏感级别、可检索性（通道、可解析）和生命周期（在用/退役）。复查日期受节奏上限约束，超期由 `sources check` 在 CI 中拦截；候选登记独立于正式来源，未准入前不得入库、索引或引用。退役保留哈希与文件，删除只用于无许可或非官方来源。

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
  cadence: monthly
  note: optional evidence sentence or review remark
```

- `source_class` says what kind of source it is, not whether it is current. `normative` covers laws, regulations and notices; `official_statistics` covers yearbook editions and statistical series; `standard` covers technical standards and operational norms; `reference` covers definitions, product documentation and other reference material.
- `currency.as_of` is the date the entry was last checked; `basis` names what that check rested on; `review_due` is when it must be checked again; `cadence` is the review rhythm that justifies that due date.
- Default review periods and v3 caps:

  | cadence | default interval | maximum `review_due - as_of` |
  |---|---|---:|
  | daily | 1 day | 3 |
  | weekly | 7 days | 21 |
  | monthly | 30 days | 60 |
  | quarterly | 90 days | 150 |
  | semiannual | 180 days | 240 |
  | annual / edition | 365 days | 400 |
  | irregular | event-driven | 180 |
  | static | no change feed | 550 |

- The 63 registered sources use the class mapping: normative `monthly`, standard `quarterly`, `official_statistics` `annual`, reference `semiannual`. The mapping is fixed in `configs/corpus.yaml` and tested in `tests/test_configs.py`.
- A `review_due` beyond the cap is a schema error, not a warning. `scs-fkb sources check --today YYYY-MM-DD` fails when an active source is more than 30 days past `review_due`; the CI job runs it with the real date. A due source is still cited, but the answer must say the source has reached its review date.
- `currency.note` carries the evidence sentence where one exists (an effective date, an approval number, a publication date) or a short review remark. It is optional, not a status field.
- There is no in-force / not-applicable / unknown state. An entry that cannot be checked keeps its existing dates, and the watch report lists it as due.
- `license` must be in the allowlist published in `configs/schema.yaml` (`public`, `internal`, `cc-by-nc-sa-3.0-igo`); `sensitivity` must be `public`, `internal` or `restricted`. Unknown values are rejected at registration, so an unlicensed page cannot silently enter the corpus.
- `authority_tier` and `level` must agree: tier `C` is municipal only, and tiers `A`/`B` are never municipal. A municipal page cannot stand in for a missing provincial or national document.

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

## 5. Admission, candidates, supersession and the main index

- **Candidate first.** A page that `watch` reports as changed, a gap found by evaluation, or a newly discovered document enters [configs/candidates.yaml](../configs/candidates.yaml) before it enters the corpus. A candidate carries `id`, `title`, `url`, `publisher`, `proposed_tier`, `proposed_class`, `reason` (`changed`/`gap`/`new`/`supersede`), `watch_ref`, `first_seen`, `expires_at`, `status` (`open`/`accepted`/`rejected`/`expired`), `decision_key`, `source_id` and a `note`. An accepted candidate must name the registered `source_id`; a rejected one must say why; a duplicate URL is rejected.
- A candidate is **not** a source. It is never ingested, indexed or cited, and `watch --propose` only writes a report; it never edits the register. Open candidates are reported after 90 days and treated as expired after `expires_at` (180 days by default).
- Admission: a publisher's own page or an official gazette attachment, a document number or publication date, a licence, a verified hash, and an accepted candidate entry.
- Supersession: a newer text supersedes but never deletes; the older entry stays with its date, the newer entry records what it replaces.
- Main index: only `level: national` (or `international`) sources with parseable text and a public or open licence may enter `configs/pipeline.yaml`. Provincial and municipal sources stay in the reference layer.

## 6. Validation

`src/scs_fkb/registry.py` loads the register and enforces schema v3: the enums, `currency.cadence` and its cap, licence and sensitivity allowlists, tier/level consistency, the retirement block and unique ids. `src/scs_fkb/candidates.py` enforces the candidate lifecycle and duplicate URLs. `scs-fkb sources check` combines both with the review-date gate; CI runs it against the real register, so a malformed, unlicensed or overdue entry fails the build rather than reaching an answer. Tests inject a fixed `--today`, so the gate is deterministic.

## 7. Fact, term and FAQ records

The internalised layer is separate from the source register and the corpus index. It is built from indexed documents, verified against their chunks and stored under `configs/facts/`, `configs/terms.yaml` and `configs/faq.yaml`.

### Fact

| Field | Type | Meaning |
|---|---|---|
| `id` | string | `FACT-<TOPIC>-<NNN>` |
| `kind` | enum | `atomic` (precise value) or `provision` (tagged article/section) |
| `topic` | enum | `policy`, `gear`, `stats`, `environment`, `hazard`, `species` |
| `question_class` | enum | `time_range`, `scope`, `operation_type`, `materials`, `procedure`, `penalty`, `inspection`, `quantity`, `definition`, `status` |
| `subject`, `predicate` | string | what the fact is about and which question facet it answers |
| `value`, `unit`, `qualifiers` | string / mapping | the answer value, unit and jurisdiction/area qualifiers |
| `effective` | mapping | `from`, `to`; null means unbounded |
| `evidence` | string | verbatim substring of the cited chunk |
| `source` | mapping | `doc`, optional `section`, `sha256` of the registered file |
| `status` | enum | `draft`, `approved`, `stale`, `superseded` |
| `confidence` | enum | `high`, `medium`, `low` |
| `as_of`, `review_due` | date | verification and next review dates |
| `supersedes` | string / null | prior fact replaced by this one |

An `approved` fact must have an A/B public source, a matching hash and verbatim evidence. Two approved facts with the same `question_class`, `subject`, `predicate` and `jurisdiction` may not overlap in effective time with different values unless one `supersedes` the other.

### Term and FAQ

- Term: `id` (`TERM-NNN`), `standard`, `variants`, `region`, `source` (`corpus`/`glossary`/`lexicon` with doc or note), `status`. The standard term must appear in the indexed corpus; variants are retrieval hints, not citations.
- FAQ: `id` (`FAQ-<PERSONA>-<NNN>`), `question`, `persona`, `claims` (fact ids), `source`, `status`. Every claim must resolve to an approved fact; no eval, gold or real-user text is used.

### Counts and validation

- 80 facts (20 atomic + 60 provision), 24 terms, 12 FAQs; rebuilt external store 375 documents / 431 chunks, index `3259a7694499`; corpus unchanged at 28 documents / 785 chunks / `20910f0964df`.
- `scs-fkb facts check --data-root "$SCS_FKB_DATA_ROOT"` verifies evidence, hashes, effective dates, conflicts and expiry; `terms check` verifies standards and sources; `faq check` verifies claims. All three exit non-zero on errors.
