clean:
	uv clean

install:
	uv sync

migrate:
	uv run manage.py migrate

makemigrations:
	uv run manage.py makemigrations

run:
	uv run daphne openwhisper.asgi:application --port 8000

run-debug:
	uv run daphne openwhisper.asgi:application --port 8000 --bind 0.0.0.0 --dev

run-tailwind:
	uv run manage.py tailwind start

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
	uv run manage.py bootstrap_superuser

collectstatic:
	uv run manage.py collectstatic --noinput

dummy-data:
	uv run manage.py bootstrap_dummy_data