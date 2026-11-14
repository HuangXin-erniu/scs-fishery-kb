.PHONY: validate lint format test build ask serve check ci

validate:
	python3 scripts/check_public_tree.py
	PYTHONPATH=src python3 scripts/check_task_cards.py
	PYTHONPATH=src python3 scripts/check_answers.py

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

test:
	pytest -q

build:
	PYTHONPATH=src python3 scripts/build_v2.py
	PYTHONPATH=src python3 scripts/build_index_v2.py

ask:
	PYTHONPATH=src python3 -m scs_fkb ask "$(Q)"

serve:
	PYTHONPATH=src python3 scripts/serve_v2.py

check: lint test validate

ci: check
