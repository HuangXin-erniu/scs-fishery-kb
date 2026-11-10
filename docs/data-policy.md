# Data Policy

> **中文摘要**：本文件说明哪些内容公开、哪些只留在本机，以及来源登记、敏感级、外部模型与运行产物的处理规则。
> `unknown` 来源一律 hold；`restricted` 来源只能本地处理，不得发送到外部模型 API。
> 公开仓库不包含数据载荷、索引、运行产物或 state 数据库。

## 1. What is published

The public repository contains:

- source code, configuration and documentation,
- the source register and schema,
- tests and validation tooling,
- no data payloads, indexes, run artifacts or state databases.

## 2. What stays local

- `$SCS_FKB_DATA_ROOT/raw/`: original documents and tables.
- `$SCS_FKB_DATA_ROOT/processed/`: parsed chunks and metadata.
- `$SCS_FKB_DATA_ROOT/index/`: local vector and keyword indexes.
- `$SCS_FKB_DATA_ROOT/web-cache/`: optional web-evidence snippets and page text.
- `$SCS_FKB_RUN_ROOT/`: local run artifacts.
- `.env`: local credentials.
- The source owner's original files remain under the owner's terms.

The data root and run root are outside the repository and are never tracked. `.env` is gitignored. The repository contains no `data/` or `runs/` directory.

## 3. Source registration

Every source must be registered in [configs/corpus.yaml](../configs/corpus.yaml) before use. The register records:

- source ID, category, title and publisher,
- year, type and format,
- location and acquisition path,
- licence and sensitivity,
- status, priority, volume, update frequency and hash,
- level, authority tier, source class, currency, retrieval channel and lifecycle (schema v2, see [data-model.md](data-model.md)).

A source with `license: unknown` or `sensitivity: unknown` is held. It must not be ingested or indexed.

## 4. Sensitivity levels

| Level | Meaning | Handling |
|---|---|---|
| `public` | May be shared publicly | May be ingested; external model use depends on `SENSITIVITY_CEILING` |
| `internal` | Owner-restricted but not secret | Owner approval; desensitise before external use |
| `restricted` | Sensitive or contract-restricted | Local only; never send to an external model API |
| `unknown` | Not yet classified | Hold; do not ingest |

## 5. Vessel and personal data

- Only data dictionaries and desensitised sample descriptions are in scope.
- Full AIS/VMS tracks are out of scope.
- Do not publish vessel identifiers, owner names, crew information or contact details.
- Aggregate or anonymise any example before it enters a document or test.
- Any sample use requires a licence and compliance review first.

## 6. External model APIs

- Only the minimum necessary retrieved evidence is sent to an external model.
- `restricted` sources are never sent externally.
- `internal` sources require owner approval and desensitisation.
- Request metadata such as model name, timestamp and token count may be logged; sensitive source text is not copied into logs.
- A local model may be used when a source cannot leave the machine.

## 6.1 Optional web retrieval

- The web layer is off by default (`SCS_FKB_WEB=off`; API default `web: "off"`).
- When it runs, the question text is sent to the configured search backend: a
  local SearXNG instance when `SEARXNG_URL` is set, otherwise DuckDuckGo. Fetched
  pages are restricted to the official-host allowlist in
  `configs/web-sources.yaml` and must use HTTPS.
- Snippets, fetched text and the evidence index stay under
  `$SCS_FKB_DATA_ROOT/web-cache/`. They are never committed, never published and
  never cited as knowledge-base evidence.
- A web result may become a source only through the candidate queue and a human
  admission review. The service never writes to `configs/corpus.yaml` and never
  ingests a page automatically.
- Questions are not logged by this layer. The service records only request
  counters and latency in `/metrics`.

## 7. Run artifacts and state

- Run outputs, indexes, logs and state databases stay local, outside the repository.
- The public repository must not contain `.db`, `.db-wal`, `.db-shm`, `.sqlite`, `.env` or run logs.
- State backups are kept outside the public repository.

## 8. Data availability

This repository does not distribute data. Access to a source depends on the source owner's licence and the project's sensitivity rules. A future data-availability statement will list only sources that can be shared lawfully.

## 9. Retention and deletion

- The project owner decides how long local source files and run artifacts are retained.
- Before deleting a source, confirm that evaluation evidence and citations remain reproducible.
- Removing a source from the public repository does not remove the owner's original copy.
- Retirement is the default for replaced, unparseable or orphaned sources: the entry keeps its id, hash and local file, moves to `lifecycle: retired` and leaves every retrieval channel.
- Hard deletion is limited to sources with no licence and no official provenance. It removes the register entry, the collection entry and the local file, and records the decision key that authorised it.

## 10. Reporting a problem

If you find data, credentials or personal information that should not be public, follow [SECURITY.md](../.github/SECURITY.md) and do not open a public issue containing the material.
