clean:
	uv clean

install:
	uv sync

migrate:
	uv run manage.py migrate

run:
	uv run daphne openwhisper.asgi:application --port 8000

run-debug:
	uv run daphne openwhisper.asgi:application --port 8000 --bind 0.0.0.0 --dev

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run djlint --check .

lint-fix:
	uv run ruff check . --fix

format:
	uv run ruff format .
	uv run djlint --reformat .

type-check:
	uv run mypy .

reset-db:
	dropdb --if-exists openwhisper -U postgres
	createdb openwhisper -U postgres
	uv run manage.py migrate
	uv run manage.py createsuperuser --noinput --username admin --email admin@example.com