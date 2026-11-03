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

Tier C never substitutes for a missing provincial or national document. When the only available text is municipal, the register says so in the entry notes.

## 3. What may enter the register

- A page or attachment under the publisher's own domain, reachable without login, with a stable URL.
- The publisher, a document number (文号) when one exists, the publication date, the source class and the date on which the page itself was checked.
- A licence the project can name. A page that states only site terms is recorded as `unknown` and held: it may be kept locally for reference but not ingested or indexed.

## 4. What may not

- News items, reposts, aggregators, WeChat posts and search-engine caches. They may point at a document; they are never the document.
- Pages behind a login, a paywall or an explicit no-copy notice.
- A rewritten or summarised version of a source. If the body text is unreachable, the gap is recorded, not filled.
- A newer text used to answer an older question without saying which version is cited.

## 5. Versions and supersession

A newer version supersedes an older one but never deletes it: the register keeps the older entry with its date and the newer entry records what it replaces. Answers cite the version actually used. A page marked 已修改 is not registered as current, which is why the Hainan 2008 page stayed out while the in-force 2013 revision entered.

## 6. The watch workflow

[configs/source-watch.yaml](../configs/source-watch.yaml) lists a curated set of authoritative pages with a tier, a publisher and an expected cadence. The national closure notice, the 2026 enforcement notice, the 2017 hull evaluation notice and the 2024 parameter-series page are seeded with recorded hashes, so their next change reports as changed. `scs-fkb watch` reads them, compares the body hash and the caching headers against the recorded baseline and writes a local report; `--offline` replays the recorded statuses without opening a socket.

The checker verifies TLS. Some networks intercept it, so the venv trust store may reject a certificate that the system keychain accepts; the checker honours `SCS_FKB_CA_BUNDLE` first, then falls back once to the system bundle on a certificate-verification error, and it never creates an unverified context. The bundle used is recorded in each result.

The coverage rule is enforced in code: every active acquired national or provincial source carries either `watch_ref` naming its watch entry or a `watch_note` explaining why it is not individually monitored. The reasons are limited to three categories — an internal data edition that is not a web page, international product documentation watched upstream, and static publisher text with no change feed that is rechecked at the quarterly review. `validate_watch_coverage` fails the test suite when a new source arrives without either field, so the monitoring surface cannot silently fall behind the register.

The checker is read-only by design. It never downloads a document into the register, never edits `configs/corpus.yaml` and never changes a collection. A change in the report is a prompt: the operator reviews the page, and if it is worth registering, the normal flow applies — decision, contract, download, hash, register, test.

## 7. Why the answer path is not allowed to fetch

Answers must be reproducible from a fixed index, citable to a specific document version and checkable against the recorded hash. A live fetch would break all three, and it would also bypass the licence check. External retrieval therefore belongs to discovery, verification and monitoring, not to answering.

## 8. The register schema

Fields, enums and lifecycle rules are defined in [data-model.md](data-model.md). In short: level separates the national basis from provincial, municipal and international material; authority tier records whether the page is the publisher's own; source_class records what kind of source it is; currency records when it was last checked and when it must be checked again; retrieval records whether the text is actually reachable; lifecycle separates active from retired. Nothing is assumed current: the review date is the contract.

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

The watch report now also lists entries and cards whose review date has arrived: `currency.review_due` for register entries and `fetched_at` plus the topic cadence for cards. The next quarterly review is **2027-02-02**. A watch entry that reports `changed` is a prompt to review the page, not an automatic update: the operator checks the page, decides whether the register needs a new entry or a currency update, and records the decision.

## 10. References

- Source register: [configs/corpus.yaml](../configs/corpus.yaml)
- Watch list: [configs/source-watch.yaml](../configs/source-watch.yaml)
- Data policy: [data-policy.md](data-policy.md)
- Corpus: [corpus.md](corpus.md)

## Web cards

The corpus is fixed at refresh time; answers never browse. External knowledge arrives as **web cards**: a card names an allowlisted URL, a topic, a publisher and a licence, and `scs-fkb web refresh` fetches it, extracts text and writes two things:

- the extracted text under `$SCS_FKB_DATA_ROOT/web/<CARD_ID>/text.txt` (private);
- the card metadata in [configs/web-cards.yaml](../configs/web-cards.yaml) — URL, title, publisher, fetch time, SHA-256, content type, licence, a 300-character excerpt and a status (public).

Only hosts in [configs/web-sources.yaml](../configs/web-sources.yaml) may be fetched: the central ministries and the four provincial governments, FAO, WoRMS, FishBase, IUCN, Copernicus Marine, NOAA and NASA Earthdata. The check is exact-host or subdomain, https only; anything else fails with a recorded reason and no request.

Refresh is manual and per topic (`species`, `gear`, `environment`, `hazard`); the default cadence is 30 days and the watch report lists cards whose review date has passed. Failures do not abort the batch: the card keeps its previous text and records the error. Nothing fetched is republished in full; the public tree carries metadata and a short excerpt only, so the licence of each page still governs its text.

A card is indexed only when its status is ok and its cached text exists: `ingest` turns it into a synthetic document with the card id, chunks the cached text and attaches the URL and fetch date to every chunk. Its citations render as `[WEB-xxx] https://… (fetched date)`, so a web-backed answer can be checked against the exact page and the day it was read. Failed or cache-less cards are skipped, never indexed as empty evidence.

The seeded cards are four WoRMS taxonomy cards for South China Sea species, one FAO ISSCFG gear-classification card, the State Council warning-signal measures page, the NASA Ocean Biology DAAC page and the EUMETSAT Sentinel-3 page, fetched on 2026-11-03. nasa.gov and eumetsat.int joined the allowlist for their own pages. Species cards are recorded as `reference` and 30-day review; the FAO card is the same. The product cards for MUR and OLCI are not seeded because their pages render through JavaScript; a later batch needs static authoritative targets.

## Operating rhythm

- **Weekly**: run `scs-fkb watch --offline` to list due corpus entries and cards; online runs when a check matters.
- **Monthly**: run `scs-fkb web refresh` for topics whose cards are due, then rebuild only if the batch is adopted.
- **Quarterly**: full review on **2027-02-02**; the next cycle's review dates are set from the outcome.
- A due item is a prompt. Nothing refreshes, rebuilds or changes an answer by itself.

## Product-manual probe (2026-11-03)

Q-E08 and Q-M09 need MUR and OLCI documents to be restored. The probe found one of the pair:

| Target | Result |
|---|---|
| EUMETSAT/ESA Sentinel-3 OLCI Marine User Handbook (earth.esa.int PDF) | reachable, 2.1 MB, parses to 88,763 characters |
| PO.DAAC MUR dataset page (podaac.jpl.nasa.gov) | TLS reset, no response |

Neither is added as a card in this batch: adding OLCI alone would add roughly ninety English chunks without restoring either question. Both questions stay parked until a reachable MUR document exists; the OLCI PDF is the first candidate once that happens, and `esa.int` would join the allowlist then.
