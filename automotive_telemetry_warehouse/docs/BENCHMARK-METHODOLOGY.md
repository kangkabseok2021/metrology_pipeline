# Benchmark Methodology — BRIN vs. B-tree, Partial-Index Selectivity

Same "honest derivation" style as `slurm-gpu-thermal-monitor`'s `FAILOVER-RUNBOOK.md`
(NVIDIA-spec-derived 83°C threshold): the numbers below this line are **measured**
locally; the 10M-row / ~1.2 GB headline figures are **derived**, not measured.

## What was measured

`make bench` runs `scripts/bench_indexes.py` against a locally generated and
loaded **~300K-1M row** dataset (a few minutes to generate/load, realistic but
manageable disk footprint) and captures real `EXPLAIN (ANALYZE, BUFFERS)` output:

| Metric                              | BRIN (`idx_fact_ts_brin`) | B-tree (ad-hoc, dropped after) |
|-------------------------------------|---------------------------|--------------------------------|
| Index size at measured row count    | *(filled in by `make bench` output)* | *(filled in by `make bench` output)* |
| 7-day range-scan execution time     | *(filled in)*             | *(filled in)*                  |

| Metric                                    | Value (measured) |
|-------------------------------------------|------------------|
| `anomaly_flag = TRUE` selectivity          | *(filled in — expected ~0.5%)* |
| `idx_fact_anomaly` partial index size      | *(filled in)*    |
| Anomaly-only scan execution time           | *(filled in)*    |

Run `make bench` and paste its stdout into the placeholders above before citing
these numbers anywhere outward-facing.

## Why the BRIN-vs-B-tree size ratio holds at 10M rows (derivation, not measurement)

A BRIN index stores one summary tuple per *block range* (default 128 pages =
1 MB), not one entry per row. Its size is therefore:

```
brin_size ≈ (table_size_bytes / (pages_per_range * 8KB)) * bytes_per_summary_tuple
```

— **proportional to `table_size / pages_per_range`**, independent of the
absolute row count. Scaling the measured table from ~300K-1M rows (~70-250 MB)
to 10M rows (~1.2 GB, assuming the same ~120-byte average row width) scales
`table_size_bytes` linearly, so `brin_size` scales linearly too — the **ratio**
`brin_size / btree_size` measured locally is expected to hold at 10M rows,
because B-tree size *also* scales roughly linearly with row count (one entry
per indexed row, plus tree-overhead that grows logarithmically). The absolute
numbers at 10M rows are therefore: `brin_size_10M ≈ brin_size_measured *
(10_000_000 / measured_row_count)`, and likewise for `btree_size_10M` — both
derived by linear extrapolation from the measured ratio, never independently
measured at 10M rows in this project.

## Why the partial-index selectivity is scale-invariant by construction

`idx_fact_anomaly` indexes only rows `WHERE anomaly_flag = TRUE`. The anomaly
rate is a property of the *generator's* physical-bounds thresholds and the 4σ
statistical pass — both percentage-based — so the **fraction** of rows flagged
(~0.5%) does not change with table size; only the absolute row count does. The
selectivity measured locally is therefore directly applicable at any scale,
including 10M rows, with no extrapolation needed.

## What this means for the 10M-row / ~1.2 GB headline figures

The headline figures quoted elsewhere in this project's docs (10M rows,
~1.2 GB fact table) are **derived** from the measured-at-scale numbers above
via the linear-extrapolation argument, not independently measured — generating
and loading 10M rows locally would take significantly longer and was judged
not worth the wall-clock cost for a portfolio benchmark whose *point* is to
demonstrate the reasoning, not to brute-force a large number.
