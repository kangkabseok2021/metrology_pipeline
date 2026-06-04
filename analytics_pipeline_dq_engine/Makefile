.PHONY: up down generate load dbt-deps dbt-run dbt-test ge-check test ci clean

DB_URL   ?= postgresql://analytics:analytics@localhost:5432/analytics
DBT_ARGS  = --project-dir dbt --profiles-dir dbt
DBT_ENV   = DBT_HOST=localhost DBT_USER=analytics DBT_PASSWORD=analytics DBT_DBNAME=analytics
ROWS      ?= 25000
CSV       ?= /tmp/raw_shipments.csv

up:
	docker compose up -d --wait

down:
	docker compose down -v

generate:
	uv run python generate_raw_data.py --rows $(ROWS) --output $(CSV)

load:
	DATABASE_URL=$(DB_URL) uv run python load_bronze.py --csv $(CSV)

dbt-deps:
	uv run dbt deps $(DBT_ARGS)

dbt-run:
	$(DBT_ENV) uv run dbt run $(DBT_ARGS)

dbt-test:
	$(DBT_ENV) uv run dbt test $(DBT_ARGS)

ge-check:
	DATABASE_URL=$(DB_URL) uv run python quality/checkpoint.py

test:
	DATABASE_URL=$(DB_URL) uv run pytest tests/ -v --tb=short

ci: up generate load dbt-deps dbt-run dbt-test test ge-check

clean:
	rm -f $(CSV)
	docker compose down -v
