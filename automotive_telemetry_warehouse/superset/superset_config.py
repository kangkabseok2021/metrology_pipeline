"""Superset config: connects to the warehouse via the least-privilege superset_ro role."""

import os

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "telemetry-demo-secret-key-change-me")

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SUPERSET_METADATA_DB_URI", "sqlite:////app/superset_home/superset.db"
)

# The fleet-telemetry source DB is registered as a Superset "database" via the
# superset_ro role — SELECT only on the two Materialized Views, no raw fact-table
# access. Connection string: postgresql+psycopg2://superset_ro:superset_ro@postgres:5432/telemetry

FEATURE_FLAGS = {
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
}
