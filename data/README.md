# Local data directory

This directory is for **local source files and indexes** only. It is not part of the
published repository.

- `data/raw/`: original documents and tables.
- `data/processed/`: parsed chunks and normalised metadata.
- `data/index/`: local vector and keyword indexes.

Only this README is tracked by Git. Every other file under `data/` is gitignored.

Rules:

- Do not commit data payloads, indexes or derived tables.
- Register every source in `configs/corpus.yaml` before use.
- Sources with `license: unknown` or `sensitivity: unknown` are held.
- `restricted` sources stay local and must not be sent to an external model API.
- Do not store full AIS/VMS tracks or personally identifying information here.

See [docs/data-policy.md](../docs/data-policy.md) for the full policy.
