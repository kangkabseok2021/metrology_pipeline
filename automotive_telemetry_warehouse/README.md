# Automotive Telemetry Data Warehouse

A containerized PostgreSQL data-warehouse + analytics stack: Star Schema design,
BRIN/partial indexes, Materialized Views, a FastAPI/SQLAlchemy analytics backend
with ETL-driven anomaly detection, Apache Superset dashboards, and
Airflow/Docker/Kubernetes orchestration.

See `docs/ARCHITECTURE.md` for the schema ERD and data flow, and
`docs/BENCHMARK-METHODOLOGY.md` for the BRIN-vs-B-tree index benchmark derivation.

## Quickstart

```bash
make up                       # start postgres + api + superset + airflow
make generate ROWS=500000     # synthetic fleet telemetry CSV
make load                     # COPY into the Star Schema
make bench                    # EXPLAIN ANALYZE BRIN-vs-B-tree comparison
make test                     # pytest-postgresql suite
```
