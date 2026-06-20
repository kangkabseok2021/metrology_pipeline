# DWH Cutover Runbook — Legacy MS SQL Server → Lakehouse

## Phase 1: Dual-Write (Weeks 1–4)

Run the Bronze extraction daily alongside the legacy DWH ETL:
```bash
JDBC_URL="jdbc:sqlserver://prod-mssql:1433;..." \
BRONZE_PATH="abfss://bronze@stinsurancelh001.dfs.core.windows.net" \
uv run python -m pipeline.run_all
```

Monitor both pipelines. Downstream BI reports should still read from the legacy DWH.

## Phase 2: Reconciliation (Week 5)

Run reconciliation queries to validate Gold against the legacy DWH:

```sql
-- Row count reconciliation
SELECT 'legacy_claims' AS source, COUNT(*) AS n FROM legacy_dw.dbo.fact_claims
UNION ALL
SELECT 'gold_claims',             COUNT(*) FROM gold.fact_claims;

-- Sum reconciliation on payout_amount
SELECT 'legacy' AS src, SUM(payout_amount) FROM legacy_dw.dbo.fact_claims
UNION ALL
SELECT 'gold',          SUM(payout_amount) FROM gold.fact_claims;
```

Acceptable tolerance: row counts within ±0.1%, sums within ±0.01%.

## Phase 3: Cutover (Week 6)

1. Freeze legacy DWH ETL writes (maintenance window, 30 min).
2. Run final Bronze→Gold pass to catch up any late-arriving records.
3. Run `quality/checkpoint.py` — must exit 0.
4. Switch BI report data sources from legacy DWH to Gold Delta tables.
5. Archive legacy DWH (read-only mode; retain for 90 days).

## Rollback Procedure

If the Gold quality gate fails post-cutover:
1. Switch BI reports back to legacy DWH (reverse the data source change).
2. Page the data engineering team.
3. Re-run `quality/checkpoint.py` with `--verbose` flag for detailed failure diagnostics.
4. Do not delete Gold Delta tables — use Delta time-travel to inspect prior versions.
