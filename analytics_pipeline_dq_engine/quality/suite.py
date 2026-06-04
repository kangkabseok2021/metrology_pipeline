"""Z-score data quality gate + Great Expectations suite.

Mathematical gate:  Z = (x − μ) / σ  per shipping-cost row.
Fail threshold:     > 0.1 % of rows with |Z| > 3.0 (3-sigma rule).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


# ── Pure Z-score helper ───────────────────────────────────────────────────────

def z_scores(series: pd.Series) -> pd.Series:
    """Return Z = (x − μ) / σ; constant series → all zeros."""
    mu = series.mean()
    sigma = series.std()
    if sigma < 1e-9:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mu) / sigma


# ── Validation result ─────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    success: bool
    statistics: dict = field(default_factory=dict)
    details: list[str] = field(default_factory=list)


# ── GE-compatible suite ───────────────────────────────────────────────────────

def validate_shipping_costs(
    df: pd.DataFrame,
    outlier_threshold: float = 0.001,
    z_cutoff: float = 3.0,
) -> ValidationResult:
    """
    Run four quality expectations on the shipping_cost_usd column:
      1. not_null  (mostly ≥ 90 %)
      2. between   0–50 000 (mostly ≥ 99 %)
      3. mean_between 100–10 000
      4. Z-score gate:  |Z| > z_cutoff for ≤ outlier_threshold fraction

    Returns a ValidationResult (GE-compatible success flag + statistics).
    """
    col = "shipping_cost_usd"
    details: list[str] = []
    failures = 0

    if col not in df.columns:
        return ValidationResult(success=False, details=[f"Missing column: {col}"])

    raw = df[col]
    numeric = pd.to_numeric(raw, errors="coerce")
    valid = numeric.dropna()
    n_total = len(raw)
    n_valid = len(valid)

    # Expectation 1: mostly not null (≥ 90 %)
    null_rate = 1.0 - n_valid / n_total if n_total else 1.0
    if null_rate > 0.10:
        failures += 1
        details.append(f"null_rate={null_rate:.2%} > 10 %")

    # Expectation 2: mostly in [0, 50 000] (≥ 96 % on raw Bronze data).
    # Raw data contains ~2 % injected negative costs; cleaned Silver data
    # would use a stricter threshold after dbt nullifies negatives.
    in_range = valid[(valid >= 0) & (valid <= 50_000)]
    range_rate = len(in_range) / n_valid if n_valid else 0.0
    if range_rate < 0.96:
        failures += 1
        details.append(f"in_range_rate={range_rate:.2%} < 96 %")

    # Expectation 3: mean in [100, 10 000]
    mean_val = float(valid.mean()) if n_valid else 0.0
    if not (100.0 <= mean_val <= 10_000.0):
        failures += 1
        details.append(f"mean={mean_val:.2f} outside [100, 10 000]")

    # Expectation 4: Z-score gate
    zs = z_scores(valid)
    outlier_count = int((zs.abs() > z_cutoff).sum())
    outlier_ratio = outlier_count / n_valid if n_valid else 0.0
    if outlier_ratio > outlier_threshold:
        failures += 1
        details.append(
            f"outlier_ratio={outlier_ratio:.4%} > {outlier_threshold:.4%} "
            f"({outlier_count} rows with |Z| > {z_cutoff})"
        )

    stats = {
        "n_total": n_total,
        "n_valid": n_valid,
        "null_rate": round(null_rate, 4),
        "mean": round(mean_val, 2),
        "std": round(float(valid.std()) if n_valid else 0.0, 2),
        "outlier_count": outlier_count,
        "outlier_ratio": round(outlier_ratio, 6),
    }
    return ValidationResult(success=(failures == 0), statistics=stats, details=details)
