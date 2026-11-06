# Data Model

> **中文摘要**：本文件定义语料登记 schema v4。每条来源必须声明层级（国家/省/市/国际/非官方）、权威等级（A/B/C/D）、来源类别（规范/官方统计/标准/参考）、来源证据（URL、文号、发布日期、抓取日期、哈希、快照）、生效期、时效（核验日期、依据、复查日期、复查节奏）、许可与敏感级别、可检索性（通道、可解析）和生命周期（在用/退役）。A/B 可作主证据，C 仅地方补充，D 仅背景/定义；付费文本用 `licensed` 并记录授权说明。v3 条目由加载器派生 v4 默认值，不丢失 id/hash。复查日期受节奏上限约束，超期由 `sources check` 在 CI 中拦截；候选登记独立于正式来源，未准入前不得入库、索引或引用。退役保留哈希与文件，删除只用于无许可或非官方来源。

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
| `source_record_schema` | integer | no | `4` for explicit v4 records; legacy records are derived to 4 by the loader |
| `level` | enum | yes | `national` / `provincial` / `municipal` / `international` / `non_official` |
| `authority_tier` | enum | yes | `A` publisher's own page, `B` gazette or official attachment or compilation, `C` municipal page (supplement only), `D` non-official expert source |
| `source_class` | enum | yes | `normative` / `official_statistics` / `standard` / `reference` |
| `provenance` | mapping | no (derived) | `url`, `document_no`, `published_at`, `retrieved_at`, `sha256`, `bytes`, `mime`, `snapshot_path`; `sha256`/`snapshot_path` derive from `hash`/`location` |
| `effective` | mapping | no (derived) | `from`, `to`; both null when open-ended |
| `quality` | mapping | no (derived) | `text_layer`, `anchors`, `tables`, `ocr`, `quarantine_reason` |
| `supersedes`, `superseded_by` | string / null | no | version lineage; never self-referential |
| `license_note` | string / null | required for `licensed` | authorisation reference; the text is not published |
| `currency` | mapping | yes | See section 2 |
| `retrieval` | mapping | yes | See section 3 |
| `lifecycle` | enum | yes | `active` / `retired` |
| `retirement` | mapping | when retired | `date`, `reason`, `decision_key` |

The file-level `schema_version` stays `1`; `source_record_schema: 4` names the
record contract. This keeps the existing loaders and fixtures valid while the
record semantics move to v4. The loader derives missing v4 fields from `hash`
and `location` and never overwrites an explicit value.

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
- `authority_tier` and `level` are a pair. A/B may be national, provincial or international. C must be municipal and is a supplement, never a substitute for a missing higher-level document. D must be `non_official` and is background or definition only; it is never primary for a rule, current status, quantity or warning.
- `license: licensed` is for paid or otherwise authorised text. It requires `license_note` (authorisation reference) and the text stays local; the register publishes metadata only.
- `provenance.sha256` must equal `hash` when both are present; `snapshot_path` must stay under the data root. `effective.from/to` are ISO dates and `to` must not precede `from`.
- `currency.as_of` is the date the entry was last checked; `basis` names what that check rested on; `review_due` is when it must be checked again; `cadence` is the review rhythm that justifies that due date.
- Default review periods and cadence caps:

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
- `license` must be in the allowlist published in `configs/schema.yaml` (`public`, `internal`, `licensed`, `cc-by-nc-sa-3.0-igo`); `sensitivity` must be `public`, `internal` or `restricted`. Unknown values are rejected at registration, so an unlicensed page cannot silently enter the corpus. `licensed` requires `license_note`.
- `authority_tier` and `level` must agree: tier `C` is municipal only; tier `D` is `non_official` only; tiers `A`/`B` are never municipal or non-official. A municipal page cannot stand in for a missing provincial or national document, and a D source is never primary for an operational claim.

### 2.1 Provenance, effective dates and quality

```yaml
provenance:
  url: https://example.org/document
  document_no: 农渔发〔2026〕1号
  published_at: '2026-01-01'
  retrieved_at: '2026-11-03'
  sha256: <64 hex>
  bytes: 1024
  mime: text/html
  snapshot_path: snapshots/POL-EXAMPLE-001/<64 hex>
effective: {from: '2026-05-01', to: null}
quality: {text_layer: true, anchors: 42, tables: 3, ocr: false, quarantine_reason: null}
```

- `provenance` is the audit trail from a citation to the bytes that were read.
  A null `url` is allowed for an owner-supplied file; a null `retrieved_at` is
  allowed for a file whose acquisition date is recorded in `acquisition`.
- `effective` is the period in which the document is in force or the edition is
  current. It is not the same as `currency.review_due`: one is legal effect, the
  other is the next check.
- `quality` records what the parser actually achieved. A quarantine reason is
  mandatory when the text layer is absent or the anchor count is zero.
- The v4 loader fills these blocks with nulls for legacy entries. A later
  review makes them explicit; the migration audit records the derivation.

## 3. Retrieval

```yaml
retrieval:
  channel: main | collection | statistics | watch | web | local | none
  parseable: true | false
  note: one sentence on where the text is reachable
```

- `main` is the frozen legal-and-technical index; `collection` is a reference collection; `statistics` is the extract pipeline; `watch` is monitored but not ingested; `web` is a curated web card; `local` is a restricted or internal-only channel; `none` means registered for provenance only.
- `parseable: false` marks image-only or otherwise unreachable text. Such a source may stay registered as provenance but must not be cited as if its text were searchable.

## 3a. Chunk v2

The v2 ingestion path adds optional fields to `Chunk` with defaults, so v1 JSONL
and existing tests still load. The child chunk remains the retrieval unit; the
parent is stored separately and used only for context expansion.

| Field | Meaning |
|---|---|
| `parent_id` | Parent section chunk id; empty for a parent and for v1 chunks |
| `chunk_type` | `text`, `parent`, `table`, `web`, `fact`, `playbook`, `faq` or `term` |
| `section_path` | Human-readable page/section path, e.g. `p.3 / 第二十六条` |
| `version_id` | `source_id` + the first 12 characters of the source hash |
| `snapshot_hash` | SHA-256 of the snapshotted file, or the tree hash for a directory |
| `authority_tier`, `level`, `source_class`, `license` | Source governance carried onto the chunk |
| `jurisdiction`, `effective_from`, `effective_to` | Applicability and legal-effect window |
| `trust` | `authoritative`, `standard` or `provisional` derived from tier/class |

Parents group children by `(doc_id, page, section)`. A parent id is stable for
the same document/page/section, so a rebuild does not renumber citations.
`src/scs_fkb/ingest_v2/chunking.py` builds the hierarchy; `src/scs_fkb/ingest.py`
and the v1 default path are unchanged.

## 3b. Dense index manifest v2

The v2 dense index is a LanceDB table built from `v2/processed/chunks.jsonl`.
Its manifest is a small JSON file under the local data root; it is never
published.

| Field | Meaning |
|---|---|
| `index_version` | First 12 hex characters of the model, dimension, chunk digest and snapshot hash |
| `built_at` | UTC build timestamp |
| `model`, `dim` | Embedding model and vector dimension |
| `chunks`, `documents`, `table_rows` | Child chunks, documents and LanceDB rows |
| `chunk_digest` | SHA-256 over the sorted chunk records; the no-op key |
| `per_document` | Per-document chunk digests; the incremental key |
| `snapshot_manifest_sha256` | Snapshot manifest used for the build |
| `build_seconds`, `peak_rss_mb` | Local build cost |
| `rebuilt`, `removed` | Documents changed or dropped in the last build |

A build with the same model, dimension, chunk digest and a live table is a no-op.
A changed or removed document deletes its old rows by `doc_id` and adds only the
new rows. The v1 index, the answer path and the evaluation set are unaffected.

## 3c. WebEvidence

The ephemeral web plane stores a metadata record and the extracted text separately.
The text stays under the local data root; the public tree sees only metadata and
short citations.

| Field | Meaning |
|---|---|
| `evidence_id` | `WEBV-<hash>` from URL and content hash |
| `url`, `canonical_url` | Requested and final URL after allowed redirects |
| `title`, `publisher`, `domain` | Page identity and allowlist publisher |
| `authority_tier`, `source_class` | Tier from the allowlist; `reference` for web text |
| `fetched_at`, `content_hash` | Fetch time and SHA-256 of the response bytes |
| `snippet`, `text_path` | Short excerpt and relative path to the local full text |
| `search_query`, `rank` | Query and provider rank |
| `ttl_days`, `status` | Freshness window and `fetched`/`failed` state |
| `promotion_candidate_id` | Empty until a human promotes the evidence |

TTLs: warning/status 7 days, rule 30, definition/identification 90,
statistics/history 365. A fresh record is reused; an expired record is refetched
or marked stale. The v1 web-card path is unchanged.

## 3d. Playbooks and provision facts

**Playbook**: `id` (`PLAY-<PERSONA>-NNN`), `title`, `persona`, `applies_to`,
`steps[]` (`order`, `action`, `detail`, `facts[]`), `documents[]`, `deadlines[]`,
`penalties[]`, `sources[]`, `status`, `review_due`. Every step's facts must be
approved; every source must be in the register.

**Provision fact**: a reviewable section-level pointer with `kind: provision`,
exact `evidence`, `source` hash/section, `status: draft`, `confidence` and a
90-day review date. The first batch added 120 draft provision facts; the
2026-11-06 review promoted 20 and kept 100 as drafts. Promoted facts carry a
`review` block; drafts do not enter the answer path.

## 4. Lifecycle

- `active` sources participate in their channel.
- `retired` sources keep their id, hash and local file, leave every retrieval channel, and carry a `retirement` block with date, reason and decision key. Retirement is for replaced, unparseable or orphaned material; it is not deletion.
- Hard deletion is reserved for sources with no licence and no official provenance. It removes the register entry, the collection entry and the local file, and records the decision that authorised it.

## 5. Admission, candidates, supersession and the main index

- **Candidate first.** A page that `watch` reports as changed, a gap found by evaluation, or a newly discovered document enters [configs/candidates.yaml](../configs/candidates.yaml) before it enters the corpus. A candidate carries `id`, `title`, `url`, `publisher`, `proposed_tier`, `proposed_class`, `reason` (`changed`/`gap`/`new`/`supersede`), `watch_ref`, `first_seen`, `expires_at`, `status` (`open`/`accepted`/`rejected`/`expired`), `decision_key`, `source_id` and a `note`. An accepted candidate must name the registered `source_id`; a rejected one must say why; a duplicate URL is rejected.
- A candidate is **not** a source. It is never ingested, indexed or cited, and `watch --propose` only writes a report; it never edits the register. Open candidates are reported after 90 days and treated as expired after `expires_at` (180 days by default).
- Admission: a publisher's own page or an official gazette attachment, a document number or publication date, a licence, a verified hash, and an accepted candidate entry.
- Supersession: a newer text supersedes but never deletes; the older entry stays with its date, the newer entry records what it replaces.
- Main index: only `level: national` (or `international`) sources with parseable text and a public or open licence may enter `configs/pipeline.yaml`. Provincial and municipal sources stay in the reference layer. D sources and `sensitivity: internal/restricted` sources never enter the public main index; D material may be used as labelled background in a local collection, and restricted material stays in a local-only channel.

## 6. Validation

`src/scs_fkb/registry.py` loads the register and enforces source schema v4: the enums, `currency.cadence` and its cap, licence and sensitivity allowlists, A/B/C/D tier and level consistency, provenance/effective/quality shapes, supersession, the retirement block and unique ids. Legacy v3 entries are normalised in memory, so a missing `provenance`, `effective` or `quality` block is derived rather than treated as an error. `scripts/migrate_v4.py` writes an audit of that derivation without rewriting the register. `src/scs_fkb/candidates.py` enforces the candidate lifecycle and duplicate URLs. `scs-fkb sources check` combines both with the review-date gate; CI runs it against the real register, so a malformed, unlicensed or overdue entry fails the build rather than reaching an answer. Tests inject a fixed `--today`, so the gate is deterministic.

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

- 200 facts (20 atomic + 180 provision; 100 approved + 100 draft), 150 terms (133 approved + 17 draft), 12 FAQs and 15 playbooks (32 steps); the v1 external store is 504 documents / 560 chunks (chunk index `c03a133b9f2e`, dense `e06fd4f9fccc5205`) and the corpus is 41 documents / 971 chunks / `43491719734d` (v2 index `7d372c2b5f47`).
- `scs-fkb facts check --data-root "$SCS_FKB_DATA_ROOT"` verifies evidence, hashes, effective dates, conflicts and expiry; `terms check` verifies standards and sources; `faq check` verifies claims. All three exit non-zero on errors.
