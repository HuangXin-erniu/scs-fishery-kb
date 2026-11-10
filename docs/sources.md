# Sources and Authority

> **中文摘要**：本文件规定什么算权威来源、什么样的页面可以进入语料登记、以及如何用受控的外部检索保持时效。
> 外部网络只用于发现、核对与监测，不在回答时抓取；新闻、转载、聚合页与需登录页面只能当线索，不能作为引用来源。

## 1. Scope

The knowledge base cites documents, not pages in general. Every citable source must be a document published by the body that owns it, registered in [configs/corpus.yaml](../configs/corpus.yaml) with a publisher, a document number where one exists, a date, a source class, a review date and a licence. This file states what may become such a source and how the project keeps itself current without turning answers into live web fetches.

## 2. Authority tiers

| Tier | What it is | Examples |
|---|---|---|
| A | A central ministry, a provincial department or a national law database page | 农业农村部, 广东省农业农村厅, 海南省农业农村厅, 国家法律法规数据库, 交通运输部海事局, 国家卫星海洋应用中心 |
| B | An official gazette index or a government-information attachment | 农业农村部公报各期, 政府信息公开附件, 公报 PDF |
| C | A municipal or county-level department page, used only as a supplement and always labelled with its level | 汕头市农业农村局, 湛江市农业农村局 |
| D | A non-official expert source: industry association, university, extension station or NGO, labelled `非官方资料` | 行业协会技术指南, 高校研究报告, 推广站培训材料 |

Tier C never substitutes for a missing provincial or national document. When the only available text is municipal, the register says so in the entry notes. Tier D is background or definition only: it is never the sole support for a rule, current status, quantity or warning, and the answer labels it as non-official.

## 3. What may enter the register

- A page or attachment under the publisher's own domain, reachable without login, with a stable URL.
- The publisher, a document number (文号) when one exists, the publication date, the source class and the date on which the page itself was checked.
- A licence the project can name. A page that states only site terms is recorded as `unknown` and held: it may be kept locally for reference but not ingested or indexed. A paid or otherwise authorised text uses `license: licensed` plus a `license_note`; its full text is never published.
- A `provenance` block with SHA-256, byte size, MIME type and snapshot path, an `effective` period where the document has legal effect, and a `quality` block recording text layer, anchors, tables and OCR status.
- An authority tier and level that agree: A/B national, provincial or international; C municipal only; D non-official only. D is labelled and never primary for an operational claim.

## 4. What may not

- News items, reposts, aggregators, WeChat posts and search-engine caches. They may point at a document; they are never the document.
- Pages behind a login, a paywall or an explicit no-copy notice.
- A rewritten or summarised version of a source. If the body text is unreachable, the gap is recorded, not filled.
- A newer text used to answer an older question without saying which version is cited.

## 5. Versions and supersession

A newer version supersedes an older one but never deletes it: the register keeps the older entry with its date and the newer entry records what it replaces. Answers cite the version actually used. A page marked 已修改 is not registered as current, which is why the Hainan 2008 page stayed out while the in-force 2013 revision entered.

## 6. The watch and candidate workflow

`configs/source-watch.yaml` lists 26 curated authoritative pages with a tier, a publisher and an expected cadence. `scripts/watch_sources.py` fetches them, compares the body hash and the caching headers with the recorded baseline and writes a report under the run root. `--offline` replays the recorded statuses without opening a socket, `--baseline` records the current hashes under `$SCS_FKB_DATA_ROOT/watch/baseline.json`, and `--propose` writes candidate drafts next to the report; it never edits the register.

The checker verifies TLS. Some networks intercept it, so the venv trust store may reject a certificate that the system keychain accepts; the checker honours `SCS_FKB_CA_BUNDLE` first, then falls back once to the system bundle on a certificate-verification error, and it never creates an unverified context. The bundle used is recorded in each result.

The coverage rule is enforced in code: every active acquired national or provincial source carries either `watch_ref` naming its watch entry or a `watch_note` explaining why it is not individually monitored. The reasons are limited to three categories — an internal data edition that is not a web page, international product documentation watched upstream, and static publisher text with no change feed that is rechecked at the quarterly review. `scripts/check_sources.py` fails when a new source arrives without either field, so the monitoring surface cannot silently fall behind the register.

The checker is read-only by design. It never downloads a document into the register, never edits `configs/corpus.yaml` and never changes a collection. A change in the report is a prompt: the operator reviews the page, and if it is worth registering, the normal flow applies — decision, contract, download, hash, register, test. The weekly cycle and the admission runbook are in [operations.md](operations.md).

### 6.1 Candidate admission

A change report does not become a source by itself. `scripts/watch_sources.py --propose` turns every `changed` or `unbaselined` entry into a proposal carrying `watch_ref`, `first_seen` and an `expires_at` 180 days out. The proposal and the watch report are written under the run root; both `configs/corpus.yaml` and `configs/candidates.yaml` stay untouched.

The proposal is reviewed as a **candidate** in [configs/candidates.yaml](../configs/candidates.yaml):

| Field | Rule |
|---|---|
| `id` | `CAND-YYYY-NNN`, unique |
| `url` | `http://` or `https://`, unique after trailing-slash normalisation |
| `reason` | `changed`, `gap`, `new` or `supersede` |
| `status` | `open`, `accepted`, `rejected` or `expired` |
| `accepted` | must name the registered `source_id` |
| `rejected` | must carry a `note` explaining why |
| `expires_at` | defaults to `first_seen + 180 days`; open past it is reported expired |

An open candidate is reported as due after 90 days. `scripts/check_sources.py` fails when an active source is past `review_due` plus a 30-day grace, when a candidate is malformed or expired, or when an accepted candidate names a source that is not in the register. Nothing is ingested automatically: acceptance still requires the decision, the download, the hash and the register entry, and only then does the source become citable.

## 7. Canonical answers and controlled web evidence

The canonical answer path does not fetch. Answers must be reproducible from a fixed index, citable to a specific document version and checkable against the recorded hash. A live fetch in that path would break all three and bypass the licence check.

A separate **ephemeral** path may query the live web when the canonical answer abstains inside a supported domain, when the question carries a freshness cue, or when the operator explicitly asks. It is restricted to the allowlist in [configs/web-sources.yaml](../configs/web-sources.yaml), records URL, publisher, fetched time, content hash and authority tier, and is labelled `网络检索 · 未入知识库`. It never enters the canonical index, never counts as a corpus citation and never changes an abstention. Promotion goes through the candidate queue and a human review; the layer prepares a draft and never writes the register. The implementation is `src/scs_fkb/web_v2/`, it is off by default (`SCS_FKB_WEB=off`), and the rules are in [rag-standard.md](rag-standard.md) section 7.

## 8. The register schema

Fields, enums and lifecycle rules are defined in [data-model.md](data-model.md). Source schema v4 adds `provenance`, `effective`, `quality`, `supersedes`/`superseded_by`, `license_note`, tier D and the `non_official` level. In short: level separates the national basis from provincial, municipal, international and non-official material; authority tier records whether the page is the publisher's own; source_class records what kind of source it is; currency records when it was last checked, when it must be checked again, and the cadence that bounds that date; licence and sensitivity are checked against the schema allowlist; retrieval records whether the text is actually reachable; lifecycle separates active from retired. Nothing is assumed current: the review date is the contract, and `scripts/check_sources.py` enforces it. Legacy v3 entries are normalised by the loader; `scripts/migrate_v4.py` writes the derivation audit.

## 9. National currency table

| Source | Status | As of | What triggers a review |
|---|---|---|---|
| `POL-LAW-009` | in force | 2026-11-02 | A further amendment to the Fisheries Law |
| `POL-CLOS-015` | in force | 2026-11-02 | A new ministry closure notice replacing 2023 年 1 号 |
| `POL-SPEC-041` | in force (2026 season) | 2026-11-02 | The 2027 special-permit notice |
| `POL-ENF-068` | in force (2026 season) | 2026-11-02 | The 2027 enforcement notice |
| `POL-OBS-072` | in force | 2026-11-02 | A new State Council revision of the observation regulation |
| `POL-RES-075` | in force | 2026-11-02 | Repeal or replacement of 农业部令第 20 号 |
| `POL-PORT-077` | in force | 2026-11-02 | A new amendment of the port traffic regulation |
| `POL-PORT-078` | current 2025 batch | 2026-11-02 | The next port-grade recognition batch |
| `STAT-ECO-073` | latest edition | 2026-11-02 | The 2026 ecological bulletin |
| `STAT-DIS-074` | latest edition | 2026-11-02 | A 2024 disaster bulletin, or a text-robust copy |
| `STD-SPEC-076` | in force | 2026-11-02 | A revised protected-wildlife list |
| `STD-YY-071` | in force | 2026-11-02 | A new distant-water parameter series |
| `POL-PEN-078` | in force | 2026-11-02 | A new revision of the penalty rules |
| `POL-LIST-079` | current | 2026-11-02 | The next annual catalogue of rules in force |
| `POL-PEN-080` | in force | 2026-11-02 | A new revision of the general penalty rules |

The weekly report lists register entries whose review date has arrived and the watch rows that are not `ok`. The next quarterly review is **2027-02-02**. A watch entry that reports `changed` is a prompt to review the page, not an automatic update: the operator checks the page, decides whether the register needs a new entry or a currency update, and records the decision. `scripts/check_sources.py` adds the hard gate: it fails when an active source is more than 30 days past `review_due`, when a candidate is malformed or expired, or when an accepted candidate points at a missing source. It runs in CI; `--today` makes the result reproducible.

## 10. References

- Source register: [configs/corpus.yaml](../configs/corpus.yaml)
- Watch list: [configs/source-watch.yaml](../configs/source-watch.yaml)
- Operations: [operations.md](operations.md)
- Data policy: [data-policy.md](data-policy.md)
- Corpus: [corpus.md](corpus.md)

## Web evidence

The ephemeral channel is not a source and not a web card. A local `SearXNG` JSON endpoint is used when `SEARXNG_URL` is set; when it returns no results or errors, the provider falls back to the DuckDuckGo client in `requirements-rag.txt`. Neither is required by CI. A `WebEvidence` record is created at query time and cached with a TTL; it carries `url`, `publisher`, `domain`, `fetched_at`, `content_hash`, `authority_tier`, `snippet`, `search_query`, `rank` and `ttl_days`. It is never written to `corpus.yaml` or the canonical index.

- **Trigger:** an explicit `web=on` request, a freshness cue (`最新`, `今年`, `现在`, `台风`, `预警`), a cited source past its review date, or an in-scope canonical abstention.
- **Allowlist:** only hosts in [configs/web-sources.yaml](../configs/web-sources.yaml); HTTPS only; non-allowlisted results are dropped and recorded. Specific central and provincial domains carry tier A/B; the generic `gov.cn` fallback is tier C and is labelled `地方政府网站（层级待核）`, so a municipal page cannot be promoted to national authority by host alone.
- **TTL:** warning/status 7 days, rule 30 days, definition/identification 90 days, statistics/history 365 days. Expired evidence is not reused.
- **Citation:** `[WEB:domain:hash8] URL (抓取于 YYYY-MM-DD)`; the UI labels it `网络检索 · 未入知识库`.
- **Promotion:** a draft is prepared for the candidate queue; the normal admission flow (licence, authority, hash, review) is still required. No automatic ingest.

The full text stays in the local web cache under `$SCS_FKB_DATA_ROOT/web-cache/`; the public tree carries metadata and a short excerpt only. Web content is treated as hostile input: scripts and invisible characters are stripped and it is never executed as an instruction. See [operations.md](operations.md) and [rag-standard.md](rag-standard.md) section 7.

## Operating rhythm

- **Weekly**: run `scripts/check_sources.py --today ...` and `scripts/weekly_report.py --today ...`. If the report lists changed or unbaselined watch rows, review them and, when warranted, record a candidate; nothing is registered automatically.
- **Monthly**: resolve open candidates before they expire, re-check sources whose review date is close, and rebuild only if a batch is adopted.
- **Quarterly**: full review on **2027-02-02**; update `as_of`, `review_due` and `cadence` from the outcome, and resolve every open candidate.
- A due item is a prompt. Nothing refreshes, rebuilds or changes an answer by itself; a candidate is not evidence until it is accepted, downloaded, hashed and registered.

## Product-manual probe (2026-11-03)

Q-E08 and Q-M09 need MUR and OLCI documents to be restored. The probe found one of the pair:

| Target | Result |
|---|---|
| EUMETSAT/ESA Sentinel-3 OLCI Marine User Handbook (earth.esa.int PDF) | reachable, 2.1 MB, parses to 88,763 characters |
| PO.DAAC MUR dataset page (podaac.jpl.nasa.gov) | TLS reset, no response |

Neither is added as a card in this batch: adding OLCI alone would add roughly ninety English chunks without restoring either question. Both questions stay parked until a reachable MUR document exists; the OLCI PDF is the first candidate once that happens, and `esa.int` would join the allowlist then.
## Knowledge notes

A card is evidence; a note is knowledge. Each note states a handful of labelled facts with a sea area, an as-of date, a review date and the sources it rests on, pinned by SHA-256. Notes are validated by `scs-fkb knowledge check`; a changed card hash or an expired hazard note marks the note stale, and stale notes are never approved or indexed. Only A-tier official sources may be approved automatically; the rest start as drafts and need a human decision. The layer and its ten-note pilot are described in [knowledge.md](knowledge.md).

## Watch run 2026-11-10

The live run after the layer was restored checked 26 pages: **20 ok and 6 changed** (`WATCH-GD-NOTICES`, `WATCH-GD-POLICY`, `WATCH-HN-HULL-2019`, `WATCH-GX-NYNCT-NOTICES`, `WATCH-GX-HYJ-NOTICES`, `WATCH-MOJ-OBSERVATION`). The changed pages stay queued for manual reading; no corpus entry changed. The run used `--baseline`, which recorded the current hashes under the data root.

## Watch run 2026-11-03

The first online run after the card layer returned **22 ok and 4 changed**. Changed means the page body hash moved; it is a review prompt, not an automatic update.

| Watch id | Status |
|---|---|
| WATCH-GD-NOTICES | changed |
| WATCH-GX-NYNCT-NOTICES | changed |
| WATCH-GX-HYJ-NOTICES | changed |
| WATCH-MOJ-OBSERVATION | changed |

The four pages stay queued for manual reading; baselines are not refreshed and no corpus entry changes until a human confirms whether a new instrument appeared. The quarterly review reminder is scheduled for 2027-02-02, and the gap file holds one entry.


## 11. Capture transport (2026-11-07)

`scripts/capture_source.py` is the only writer for raw source snapshots. It
refuses non-HTTPS URLs and hosts outside the official allowlist, keeps existing
snapshots untouched unless `--force` is passed, and prints the provenance block
the register expects.

Two publishers (the Qinzhou marine bureau and a procuratorate reprint of the
filing standard) serve no HTTPS. `--allow-http` permits plain HTTP only for
allowlisted `.gov.cn` hosts and the entry notes record the transport; the flag is
never used for a host that supports TLS.


## 12. Batch 2 capture notes (2026-11-07)

Eight documents were captured with `scripts/capture_source.py`. Two publishers
serve no TLS for the local client (the criminal-law reprint on a municipal
letters-and-visits page and the Guangxi policy PDF), so `--allow-http` was used
and the transport is recorded in the entry notes. The wildlife-crime
interpretation is the Supreme People's Court gazette text; the criminal law is a
municipal reprint of the national statute. Neither is a news summary.
