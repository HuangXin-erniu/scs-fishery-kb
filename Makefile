.PHONY: validate lint format test sources-check check ci ingest retrieve eval define

validate:
	python3 scripts/check_public_tree.py

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

test:
	pytest -q

sources-check:
	PYTHONPATH=src python3 -m scs_fkb sources check

ingest:
	PYTHONPATH=src python3 -m scs_fkb ingest

retrieve:
	PYTHONPATH=src python3 -m scs_fkb retrieve "$(Q)"

eval:
	PYTHONPATH=src python3 -m scs_fkb eval

define:
	PYTHONPATH=src python3 -m scs_fkb define "$(TERM)"

check: lint test validate sources-check

ci: check
