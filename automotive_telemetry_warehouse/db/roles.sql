-- Least-privilege read-only role for Superset: SELECT on the Materialized
-- Views only — no raw fact-table access.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'superset_ro') THEN
        CREATE ROLE superset_ro LOGIN PASSWORD 'superset_ro';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE telemetry TO superset_ro;
GRANT USAGE ON SCHEMA public TO superset_ro;
GRANT SELECT ON mv_battery_health_daily TO superset_ro;
GRANT SELECT ON mv_fleet_geo_hourly TO superset_ro;
GRANT SELECT ON mv_vehicle_last_position TO superset_ro;
