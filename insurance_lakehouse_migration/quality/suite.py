"""Z-score data quality gate for Gold tables — follows analytics_pipeline_dq_engine pattern."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class ValidationResult:
    success: bool
    statistics: dict = field(default_factory=dict)
    details: list[str] = field(default_factory=list)


def z_scores(series: pd.Series) -> pd.Series:
    """Return Z = (x − μ) / σ; constant series → all zeros."""
    mu = series.mean()
    sigma = series.std()
    if sigma < 1e-9:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mu) / sigma


def validate_gold_tables(
    fact_claims: pd.DataFrame,
    fact_premiums: pd.DataFrame,
    dim_policy: pd.DataFrame,
    outlier_threshold: float = 0.001,
    z_cutoff: float = 3.0,
) -> ValidationResult:
    """
    Run four quality expectations on Gold tables:
      1. No null FKs in fact_claims (policy_sk, customer_sk, date_sk)
      2. No null FKs in fact_premiums (policy_sk, date_sk)
      3. Referential integrity: fact_claims.policy_sk ∈ dim_policy.policy_sk
      4. Z-score gate on fact_claims.payout_amount (|Z| > z_cutoff for ≤ outlier_threshold)
    """
    details: list[str] = []
    failures = 0
    valid_sks = set(dim_policy["policy_sk"])

    for col in ["policy_sk", "customer_sk", "date_sk"]:
        if col not in fact_claims.columns:
            continue
        n = fact_claims[col].isna().sum()
        if n > 0:
            failures += 1
            details.append(f"fact_claims.{col}: {n} null FK values")

    for col in ["policy_sk", "date_sk"]:
        if col not in fact_premiums.columns:
            continue
        n = fact_premiums[col].isna().sum()
        if n > 0:
            failures += 1
            details.append(f"fact_premiums.{col}: {n} null FK values")

    if "policy_sk" in fact_claims.columns:
        non_null = fact_claims["policy_sk"].dropna()
        orphans = (~non_null.isin(valid_sks)).sum()
        if orphans > 0:
            failures += 1
            details.append(f"fact_claims: {orphans} orphaned policy_sk values")

    if "policy_sk" in fact_premiums.columns:
        non_null = fact_premiums["policy_sk"].dropna()
        orphans = (~non_null.isin(valid_sks)).sum()
        if orphans > 0:
            failures += 1
            details.append(f"fact_premiums: {orphans} orphaned policy_sk values")

    if "payout_amount" in fact_claims.columns:
        payouts = fact_claims["payout_amount"].dropna()
    else:
        payouts = pd.Series([], dtype=float)
    n_total = len(payouts)
    outlier_count = 0
    outlier_ratio = 0.0
    if n_total > 0:
        zs = z_scores(payouts)
        outlier_count = int((zs.abs() > z_cutoff).sum())
        outlier_ratio = outlier_count / n_total
        if outlier_ratio > outlier_threshold:
            failures += 1
            details.append(
                f"fact_claims.payout_amount: outlier_ratio={outlier_ratio:.4%}"
                f" > {outlier_threshold:.4%}"
                f" ({outlier_count} rows with |Z| > {z_cutoff})"
            )

    stats = {
        "fact_claims_rows": len(fact_claims),
        "fact_premiums_rows": len(fact_premiums),
        "payout_outlier_count": outlier_count,
        "payout_outlier_ratio": round(outlier_ratio, 6),
    }
    return ValidationResult(success=(failures == 0), statistics=stats, details=details)
