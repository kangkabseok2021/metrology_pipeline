-- Star Schema: fact_telemetry + dim_vehicle + dim_time, plus BRIN/partial
-- indexes and Materialized Views. Hand-written DDL — no ORM migrations, no dbt.

CREATE TABLE IF NOT EXISTS dim_vehicle (
    vehicle_key          SERIAL PRIMARY KEY,
    vehicle_id           UUID NOT NULL UNIQUE,
    model                VARCHAR(32) NOT NULL,
    manufacture_year     INT NOT NULL,
    battery_capacity_kwh NUMERIC(5,1) NOT NULL,
    region               VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_time (
    time_key     SERIAL PRIMARY KEY,
    ts           TIMESTAMPTZ NOT NULL UNIQUE,
    date         DATE NOT NULL,
    hour         SMALLINT NOT NULL,
    day_of_week  SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_telemetry (
    event_id       BIGSERIAL PRIMARY KEY,
    vehicle_key    INT NOT NULL REFERENCES dim_vehicle(vehicle_key),
    time_key       INT NOT NULL REFERENCES dim_time(time_key),
    ts             TIMESTAMPTZ NOT NULL,
    battery_temp_c NUMERIC(5,2) NOT NULL,
    soc_pct        NUMERIC(5,4) NOT NULL,
    rpm            INT NOT NULL,
    lat            NUMERIC(9,6) NOT NULL,
    lon            NUMERIC(9,6) NOT NULL,
    anomaly_flag   BOOLEAN NOT NULL DEFAULT FALSE
);

-- BRIN: ts is sequentially inserted (load order == time order) -> near-zero
-- storage cost block-range index, see docs/BENCHMARK-METHODOLOGY.md
CREATE INDEX IF NOT EXISTS idx_fact_ts_brin
    ON fact_telemetry USING BRIN (ts);

-- Partial: anomaly_flag = TRUE covers ~0.5% of rows -> tiny, highly selective
CREATE INDEX IF NOT EXISTS idx_fact_anomaly
    ON fact_telemetry (vehicle_key)
    WHERE anomaly_flag = TRUE;

CREATE INDEX IF NOT EXISTS idx_fact_vehicle_key ON fact_telemetry (vehicle_key);
CREATE INDEX IF NOT EXISTS idx_fact_time_key ON fact_telemetry (time_key);

-- ── Materialized Views ───────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_battery_health_daily AS
SELECT
    v.vehicle_id,
    v.model,
    d.date AS day,
    AVG(f.battery_temp_c)                                            AS avg_temp_c,
    MAX(f.battery_temp_c)                                            AS max_temp_c,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY f.battery_temp_c)   AS p95_temp_c,
    AVG(AVG(f.battery_temp_c)) OVER (
        PARTITION BY v.vehicle_id ORDER BY d.date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )                                                                AS rolling_7d_avg_temp_c
FROM fact_telemetry f
JOIN dim_vehicle v ON v.vehicle_key = f.vehicle_key
JOIN dim_time d ON d.time_key = f.time_key
GROUP BY v.vehicle_id, v.model, d.date
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_battery_health_daily
    ON mv_battery_health_daily (vehicle_id, day);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_fleet_geo_hourly AS
SELECT
    d.date,
    d.hour,
    v.model,
    ROUND(f.lat, 1) AS lat_bucket,
    ROUND(f.lon, 1) AS lon_bucket,
    COUNT(*) AS event_count
FROM fact_telemetry f
JOIN dim_vehicle v ON v.vehicle_key = f.vehicle_key
JOIN dim_time d ON d.time_key = f.time_key
GROUP BY d.date, d.hour, v.model, lat_bucket, lon_bucket
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_fleet_geo_hourly
    ON mv_fleet_geo_hourly (date, hour, model, lat_bucket, lon_bucket);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vehicle_last_position AS
SELECT DISTINCT ON (v.vehicle_id)
    v.vehicle_id,
    v.model,
    f.ts,
    f.lat,
    f.lon,
    f.battery_temp_c,
    f.soc_pct
FROM fact_telemetry f
JOIN dim_vehicle v ON v.vehicle_key = f.vehicle_key
ORDER BY v.vehicle_id, f.ts DESC
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_vehicle_last_position
    ON mv_vehicle_last_position (vehicle_id);
