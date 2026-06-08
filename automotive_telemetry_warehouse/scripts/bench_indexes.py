"""BRIN-vs-B-tree and partial-index benchmark — real EXPLAIN (ANALYZE, BUFFERS).

Per the agreed approach: generate/load ~300K-1M rows locally, then run real
comparisons and print a markdown table that feeds docs/BENCHMARK-METHODOLOGY.md.
Honest derivation only — never inflate the locally-measured numbers.
"""

from __future__ import annotations

import argparse
import os
import re

import psycopg2

DB_URL = os.environ.get("DATABASE_URL", "postgresql://telemetry:telemetry@localhost:5432/telemetry")


def _index_size(cur, index_name: str) -> str:
    cur.execute("SELECT pg_size_pretty(pg_relation_size(%s))", (index_name,))
    return cur.fetchone()[0]


def _explain_scan_time_ms(cur, sql: str) -> float:
    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}")
    plan = "\n".join(row[0] for row in cur.fetchall())
    match = re.search(r"Execution Time: ([\d.]+) ms", plan)
    if not match:
        raise RuntimeError(f"could not parse execution time from plan:\n{plan}")
    return float(match.group(1))


def run_benchmark(database_url: str) -> dict:
    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    results: dict[str, object] = {}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fact_telemetry")
            results["row_count"] = cur.fetchone()[0]

            results["brin_size"] = _index_size(cur, "idx_fact_ts_brin")
            results["brin_scan_ms"] = _explain_scan_time_ms(
                cur,
                "SELECT COUNT(*) FROM fact_telemetry "
                "WHERE ts BETWEEN '2025-01-01' AND '2025-01-08'",
            )

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_fact_ts_btree_bench "
                "ON fact_telemetry USING BTREE (ts)"
            )
            results["btree_size"] = _index_size(cur, "idx_fact_ts_btree_bench")
            results["btree_scan_ms"] = _explain_scan_time_ms(
                cur,
                "SELECT COUNT(*) FROM fact_telemetry "
                "WHERE ts BETWEEN '2025-01-01' AND '2025-01-08'",
            )
            cur.execute("DROP INDEX IF EXISTS idx_fact_ts_btree_bench")

            cur.execute(
                "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE anomaly_flag) / COUNT(*), 3) "
                "FROM fact_telemetry"
            )
            results["anomaly_pct"] = cur.fetchone()[0]
            results["partial_index_size"] = _index_size(cur, "idx_fact_anomaly")
            results["partial_scan_ms"] = _explain_scan_time_ms(
                cur, "SELECT COUNT(*) FROM fact_telemetry WHERE anomaly_flag = TRUE"
            )
    finally:
        conn.close()
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="BRIN-vs-B-tree + partial-index benchmark")
    ap.add_argument("--rows", type=int, default=500_000, help="rows expected to be loaded (for the report header)")
    ap.add_argument("--db", default=DB_URL)
    args = ap.parse_args()

    r = run_benchmark(args.db)
    print(f"Measured at {r['row_count']:,} rows (target {args.rows:,}):")
    print(f"  BRIN  index size={r['brin_size']:>10}  7-day scan={r['brin_scan_ms']:.2f} ms")
    print(f"  B-tree index size={r['btree_size']:>10}  7-day scan={r['btree_scan_ms']:.2f} ms")
    print(f"  anomaly_flag selectivity = {r['anomaly_pct']}%")
    print(f"  partial index size={r['partial_index_size']:>10}  scan={r['partial_scan_ms']:.2f} ms")


if __name__ == "__main__":
    main()
