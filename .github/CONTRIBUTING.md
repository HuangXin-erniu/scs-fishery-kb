# Contributing to SCS-FKB

Thank you for your interest in the South China Sea Nearshore Fishery Knowledge Base
(SCS-FKB). This project welcomes documentation, corpus, retrieval and evaluation
contributions that fit its knowledge-layer scope.

## Before you start

- Read [PROJECT.md](../PROJECT.md) for scope and non-goals.
- Read [docs/data-policy.md](../docs/data-policy.md) before proposing any corpus source.
- Do not submit data payloads, indexes, run artifacts, credentials or restricted material.
- For a substantial change, open an issue first so the scope can be agreed.

## Development setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Checks

Run the same checks as CI before opening a pull request:

```sh
make lint
make test
make validate
```

- `make lint` runs `ruff check` and `ruff format --check`.
- `make test` runs `pytest`.
- `make validate` runs `scripts/check_public_tree.py` (required files, YAML, links, absolute paths, data/run leakage and secret patterns).

## Versioning

This project has no versioned releases. Do not add version numbers, tags or GitHub
Release notes. `main` is the supported line; changes are recorded by date in
[docs/project-log.md](../docs/project-log.md).

## Data and privacy

- Never commit `data/` payloads, `runs/`, `.env`, databases or credentials.
- Register every proposed source in `configs/corpus.yaml` with title, publisher, year,
  format, licence, sensitivity, status and acquisition notes.
- Sources with `license: unknown` or `sensitivity: unknown` stay on hold.
- `restricted` sources must stay local and must not be sent to an external model API.
- Do not submit full AIS/VMS tracks or vessel-identifying information.
- Remove personal information before proposing examples.

## Pull requests

- Keep changes focused; do not mix unrelated refactors.
- Add or update tests for configuration, validation or retrieval behaviour.
- Update documentation when scope, fields or workflows change.
- Confirm that `make lint`, `make test` and `make validate` pass.
- Describe what changed, why, and what evidence supports it.

## Commit messages

Use a short imperative subject line, for example:

```text
Add corpus licence fields
Fix citation link validation
Document abstention behaviour
```

## Issues

Use the issue templates for bugs, feature requests and data-source proposals. For
security reports, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
