"""4 pytest tests: raw data generator statistics."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from generate_raw_data import generate_raw_data


@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    return generate_raw_data(n_rows=5_000, seed=99)


def test_output_has_correct_minimum_columns(sample_df: pd.DataFrame) -> None:
    required = {
        "shipment_id", "origin_hub", "destination_hub", "product_sku",
        "carrier", "ship_date", "weight_kg", "quantity", "shipping_cost_usd",
    }
    assert required.issubset(set(sample_df.columns))


def test_null_rate_in_expected_range(sample_df: pd.DataFrame) -> None:
    """Null shipping_cost_usd rate should be 3–8 % after injection."""
    null_rate = sample_df["shipping_cost_usd"].isna().mean()
    assert 0.03 <= null_rate <= 0.08, f"null_rate={null_rate:.2%} outside [3%, 8%]"


def test_negative_costs_present(sample_df: pd.DataFrame) -> None:
    numeric = pd.to_numeric(sample_df["shipping_cost_usd"], errors="coerce")
    assert (numeric < 0).any(), "Expected at least one negative shipping cost"


def test_duplicate_rows_present(sample_df: pd.DataFrame) -> None:
    key_cols = ["origin_hub", "destination_hub", "product_sku", "carrier", "ship_date"]
    dupes = sample_df.duplicated(subset=key_cols, keep=False).sum()
    assert dupes >= 1, "Expected at least one duplicate row on key columns"
