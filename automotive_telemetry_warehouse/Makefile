.PHONY: up down generate load bench dashboards test ci clean

DB_URL  ?= postgresql://telemetry:telemetry@localhost:5432/telemetry
ROWS    ?= 500000
CSV     ?= /tmp/telemetry.csv

up:
	docker compose up -d --wait

down:
	docker compose down -v

generate:
	uv run python scripts/generate_telemetry.py --rows $(ROWS) --output $(CSV)

load:
	DATABASE_URL=$(DB_URL) uv run python scripts/load_warehouse.py --csv $(CSV)

bench:
	DATABASE_URL=$(DB_URL) uv run python scripts/bench_indexes.py --rows $(ROWS)

dashboards:
	docker compose exec superset superset import-dashboards -p /app/dashboards/fleet_telemetry.json -u admin

test:
	uv run pytest tests/ -v --tb=short

ci: test

clean:
	rm -f $(CSV)
	docker compose down -v
