.PHONY: validate lint format test check ci

validate:
	python3 scripts/check_public_tree.py

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

test:
	pytest -q

check: lint test validate

ci: check
