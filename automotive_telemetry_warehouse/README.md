# Automotive Telemetry Data Warehouse

A containerized PostgreSQL data-warehouse + analytics stack: Star Schema design,
BRIN/partial indexes, Materialized Views, a FastAPI/SQLAlchemy analytics backend
with ETL-driven anomaly detection, Apache Superset dashboards, and
Airflow/Docker/Kubernetes orchestration.

See `docs/ARCHITECTURE.md` for the schema ERD and data flow, and
`docs/BENCHMARK-METHODOLOGY.md` for the BRIN-vs-B-tree index benchmark derivation.

## Quickstart

```bash
make up                       # start postgres + api + superset + airflow;
                              # the loader service auto-generates and loads ~500K rows
make bench                    # EXPLAIN ANALYZE BRIN-vs-B-tree comparison
make test                     # pytest-postgresql suite
make dashboards               # provision the Superset Fleet Telemetry dashboard

# Optional: reload with a different row count (appends to the existing data)
make generate ROWS=1000000 && make load
```
