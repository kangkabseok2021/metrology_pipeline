.PHONY: up down seed test lint

MSSQL_URL ?= mssql+pymssql://sa:Str0ngP%40ssw0rd%21@localhost:1433/InsuranceDB

up:
	docker compose up -d --wait

down:
	docker compose down -v

seed:
	MSSQL_URL=$(MSSQL_URL) uv run python -m seed.generator

test:
	uv run pytest tests/ -v --tb=short -m "not integration"

lint:
	uv run ruff check .
