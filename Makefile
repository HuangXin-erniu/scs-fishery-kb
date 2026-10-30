.PHONY: validate lint test ci

validate:
	python3 scripts/check_public_tree.py

lint:
	ruff check .
	ruff format --check .

test:
	pytest -q

ci: lint test validate
