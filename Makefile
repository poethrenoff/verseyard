MANAGE=uv run src/manage.py

build:
	@docker compose -f docker-compose.yml build

up:
	@docker compose -f docker-compose.yml up

stop:
	@docker compose -f docker-compose.yml stop

down:
	@docker compose -f docker-compose.yml down

format:
	@uv run ruff format src && uv run ruff check --fix src

update:
	@uv sync --upgrade

makemigrations:
	@$(MANAGE) makemigrations

migrate:
	@$(MANAGE) migrate

test:
	@$(MANAGE) test src --keepdb

loaddata:
	@$(MANAGE) loaddata admins schedules

worker:
	@cd src; uv run celery -A config worker -Q celery -l INFO

worker-embeddings:
	@cd src; HF_HOME=./../.model_cache SENTENCE_TRANSFORMERS_HOME=./../.model_cache uv run celery -A config worker -Q embeddings -c 1 --pool=solo -l INFO

backfill:
	@cd src; HF_HOME=./../.model_cache SENTENCE_TRANSFORMERS_HOME=./../.model_cache uv run manage.py backfill_embeddings

beat:
	@cd src; uv run celery -A config beat -l INFO

backup:
	@bin/backup .data

restore:
	@bin/restore .data
