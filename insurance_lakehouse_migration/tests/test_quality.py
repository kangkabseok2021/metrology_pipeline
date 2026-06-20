"""Tests for Z-score quality suite (pure Python, no Spark)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1]))


def test_z_scores_known_values() -> None:
    from quality.suite import z_scores

    s = pd.Series([-2.0, -1.0, 0.0, 1.0, 2.0])
    zs = z_scores(s)
    expected = (s - s.mean()) / s.std()
    np.testing.assert_allclose(zs.values, expected.values, atol=1e-9)


def test_z_scores_constant_series_returns_zeros() -> None:
    from quality.suite import z_scores

    zs = z_scores(pd.Series([42.0] * 100))
    assert (zs == 0.0).all()


def test_validate_gold_tables_passes_clean_data() -> None:
    from quality.suite import validate_gold_tables

    rng = np.random.default_rng(0)
    n = 200
    fact_claims = pd.DataFrame({
        "policy_sk": rng.integers(1, 10, n),
        "customer_sk": rng.integers(1, 5, n),
        "date_sk": [20230101] * n,
        "claim_id": range(1, n + 1),
        "payout_amount": rng.uniform(100, 5000, n),
        "is_correction": [False] * n,
    })
    fact_premiums = pd.DataFrame({
        "policy_sk": rng.integers(1, 10, 50),
        "date_sk": [20230101] * 50,
        "invoice_id": range(1, 51),
        "amount": rng.uniform(50, 500, 50),
    })
    dim_policy = pd.DataFrame({"policy_sk": list(range(1, 11))})

    result = validate_gold_tables(fact_claims, fact_premiums, dim_policy)
    assert result.success is True


def test_validate_gold_tables_fails_on_null_fks() -> None:
    from quality.suite import validate_gold_tables

    fact_claims = pd.DataFrame({
        "policy_sk": [None, 1],
        "customer_sk": [1, 1],
        "date_sk": [20230101, 20230101],
        "claim_id": [1, 2],
        "payout_amount": [100.0, 200.0],
        "is_correction": [False, False],
    })
    fact_premiums = pd.DataFrame({
        "policy_sk": [1], "date_sk": [20230101], "invoice_id": [1], "amount": [50.0]
    })
    dim_policy = pd.DataFrame({"policy_sk": [1]})

    result = validate_gold_tables(fact_claims, fact_premiums, dim_policy)
    assert result.success is False
    assert any("null" in d.lower() for d in result.details)


def test_validate_gold_tables_fails_on_outlier_payout() -> None:
    from quality.suite import validate_gold_tables

    rng = np.random.default_rng(1)
    n = 1000
    payouts = list(rng.uniform(100, 5000, n))
    mean, std = np.mean(payouts), np.std(payouts)
    payouts += [mean + 9 * std, mean - 9 * std]  # inject 2 extreme outliers

    fact_claims = pd.DataFrame({
        "policy_sk": [1] * (n + 2),
        "customer_sk": [1] * (n + 2),
        "date_sk": [20230101] * (n + 2),
        "claim_id": range(n + 2),
        "payout_amount": payouts,
        "is_correction": [False] * (n + 2),
    })
    fact_premiums = pd.DataFrame({
        "policy_sk": [1], "date_sk": [20230101], "invoice_id": [1], "amount": [50.0]
    })
    dim_policy = pd.DataFrame({"policy_sk": [1]})

    result = validate_gold_tables(fact_claims, fact_premiums, dim_policy)
    assert result.success is False
    assert result.statistics["payout_outlier_count"] >= 2
