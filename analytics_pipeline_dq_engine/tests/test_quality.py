"""4 pytest tests: Z-score math + GE suite validation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from quality.suite import ValidationResult, validate_shipping_costs, z_scores


# ── Z-score unit tests ────────────────────────────────────────────────────────

def test_z_scores_known_values() -> None:
    """Z-score of [-2,-1,0,1,2] with μ=0, σ=1 should return itself."""
    series = pd.Series([-2.0, -1.0, 0.0, 1.0, 2.0], dtype=float)
    zs = z_scores(series)
    expected = np.array([-2.0, -1.0, 0.0, 1.0, 2.0]) / series.std()
    np.testing.assert_allclose(zs.values, expected, atol=1e-9)


def test_z_score_constant_series_returns_zeros() -> None:
    """Constant series → σ < ε → all zeros (no division by zero)."""
    series = pd.Series([42.0] * 100)
    zs = z_scores(series)
    assert (zs == 0.0).all()


# ── GE suite tests ────────────────────────────────────────────────────────────

def _clean_df(n: int = 1_000) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "shipping_cost_usd": rng.uniform(50.0, 4_000.0, size=n),
    })


def test_ge_suite_passes_clean_data() -> None:
    df = _clean_df(1_000)
    result = validate_shipping_costs(df)
    assert result.success is True
    assert result.statistics["outlier_ratio"] <= 0.001


def test_ge_suite_rejects_extreme_outliers() -> None:
    """Injecting a row at mean + 8σ should exceed the 0.1% outlier gate."""
    df = _clean_df(1_000)
    mean = df["shipping_cost_usd"].mean()
    std = df["shipping_cost_usd"].std()
    # Inject 2 extreme outliers (|Z| ≈ 8) — 0.2% of 1000 rows > 0.1% threshold
    outliers = pd.DataFrame({"shipping_cost_usd": [mean + 8 * std, mean - 8 * std]})
    df_dirty = pd.concat([df, outliers], ignore_index=True)

    result = validate_shipping_costs(df_dirty)
    assert result.success is False
    assert result.statistics["outlier_count"] >= 2
