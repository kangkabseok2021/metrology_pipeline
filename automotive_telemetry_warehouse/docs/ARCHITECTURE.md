# Architecture — Automotive Telemetry Data Warehouse

## Star Schema ERD

```
                    ┌──────────────────┐
                    │   dim_vehicle    │
                    ├──────────────────┤
                    │ vehicle_key  PK  │
                    │ vehicle_id   UQ  │
                    │ model            │
                    │ manufacture_year │
                    │ battery_capacity │
                    │ region           │
                    └────────┬─────────┘
                             │ 1
                             │
                             │ N
                    ┌────────┴─────────┐         ┌──────────────────┐
                    │  fact_telemetry  │ N     1 │     dim_time     │
                    ├──────────────────┤─────────┼──────────────────┤
                    │ event_id     PK  │         │ time_key     PK  │
                    │ vehicle_key  FK  │         │ ts           UQ  │
                    │ time_key     FK  │         │ date             │
                    │ ts                BRIN idx │ hour             │
                    │ battery_temp_c   │         │ day_of_week      │
                    │ soc_pct          │         └──────────────────┘
                    │ rpm              │
                    │ lat / lon        │
                    │ anomaly_flag      partial idx (WHERE = TRUE)
                    └──────────────────┘
```

## Data flow

```
generate_telemetry.py ──CSV──> load_warehouse.py ──COPY──> dim_vehicle/dim_time/fact_telemetry
                                       │
                                       └─ pg_notify('etl_complete', run_id)
                                                  │
                                                  ▼
                              api/etl/anomaly.py LISTEN worker
                                  physical-bounds pass (UPDATE ... WHERE temp/rpm out of range)
                                  4-sigma per-(vehicle, day) statistical pass
                                                  │
                                                  ▼
        Airflow DAG (nightly @ 02:00 UTC)  REFRESH MATERIALIZED VIEW CONCURRENTLY
          mv_battery_health_daily / mv_fleet_geo_hourly / mv_vehicle_last_position
                                                  │
                          ┌───────────────────────┴────────────────────────┐
                          ▼                                                 ▼
           FastAPI /api/fleet/* endpoints                    Superset (superset_ro role)
        (battery-health, geo-distribution,                line/box charts + deck.gl heatmap
         per-vehicle timeline — SQLAlchemy Core)                  + scatter-plot
```

## Why these index choices

- **BRIN on `ts`**: rows are inserted in roughly chronological order (the
  loader processes the generator's output in timestamp order per vehicle
  batch), so a block-range index summary captures the min/max `ts` per 1 MB
  page range at a fraction of a B-tree's storage cost. See
  `docs/BENCHMARK-METHODOLOGY.md` for measured numbers and the scale-invariance
  derivation.
- **Partial index on `anomaly_flag = TRUE`**: anomalies are ~0.5% of rows: a
  full B-tree over the boolean column would be mostly-FALSE noise; the partial
  index covers only the rows analysts actually query for.
- **Materialized Views, not live aggregation**: `fact_telemetry` is large
  (target ~10M rows / ~1.2 GB at full scale); recomputing daily battery-health
  rollups or hourly geo-buckets on every API request would mean scanning the
  whole fact table per request. The MVs precompute these once nightly via
  Airflow, and `REFRESH ... CONCURRENTLY` means readers never block.
