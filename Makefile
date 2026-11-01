.PHONY: validate lint format test check ci ingest retrieve eval define

validate:
	python3 scripts/check_public_tree.py

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

test:
	pytest -q

ingest:
	PYTHONPATH=src python3 -m scs_fkb ingest

retrieve:
	PYTHONPATH=src python3 -m scs_fkb retrieve "$(Q)"

eval:
	PYTHONPATH=src python3 -m scs_fkb eval

define:
	PYTHONPATH=src python3 -m scs_fkb define "$(TERM)"

check: lint test validate

ci: check
