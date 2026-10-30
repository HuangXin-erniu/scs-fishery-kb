# Data Policy

## 1. What is published

The public repository contains:

- source code, configuration and documentation,
- the source register and schema,
- tests and validation tooling,
- no data payloads, indexes, run artifacts or state databases.

## 2. What stays local

- `data/raw/`: original documents and tables.
- `data/processed/`: parsed chunks and metadata.
- `data/index/`: local vector and keyword indexes.
- `runs/`: local run artifacts.
- `.env`: local credentials.
- The source owner's original files remain under the owner's terms.

Only `data/README.md` is tracked. Every other file under `data/` and the entire `runs/` directory are gitignored.

## 3. Source registration

Every source must be registered in [configs/corpus.yaml](../configs/corpus.yaml) before use. The register records:

- source ID, category, title and publisher,
- year, type and format,
- location and acquisition path,
- licence and sensitivity,
- status, priority, volume, update frequency and hash.

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

## 7. Run artifacts and state

- Run outputs, indexes, logs and state databases stay local.
- The public repository must not contain `.db`, `.db-wal`, `.db-shm`, `.sqlite`, `.env` or run logs.
- State backups are kept outside the public repository.

## 8. Data availability

This repository does not distribute data. Access to a source depends on the source owner's licence and the project's sensitivity rules. A future data-availability statement will list only sources that can be shared lawfully.

## 9. Retention and deletion

- The project owner decides how long local source files and run artifacts are retained.
- Before deleting a source, confirm that evaluation evidence and citations remain reproducible.
- Removing a source from the public repository does not remove the owner's original copy.

## 10. Reporting a problem

If you find data, credentials or personal information that should not be public, follow [SECURITY.md](../SECURITY.md) and do not open a public issue containing the material.
