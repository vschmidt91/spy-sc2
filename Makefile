check:
	poetry run ruff check
	poetry run mypy .

fix:
	poetry run ruff check --fix --unsafe-fixes
	poetry run ruff format

test:
	poetry run python -m unittest discover tests