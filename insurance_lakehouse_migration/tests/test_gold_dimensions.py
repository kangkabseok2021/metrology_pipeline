"""Tests for Gold-layer dimension builders."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from pyspark.sql import Row, SparkSession

sys.path.insert(0, str(Path(__file__).parents[1]))


def _make_policies(spark: SparkSession):
    return spark.createDataFrame([
        Row(policy_id="p1", customer_id="c1", policy_type="Home", premium_amount=500.0,
            start_date=date(2022, 1, 1), end_date=date(2023, 1, 1), status_code=1,
            policy_version=1, renewal_of_policy_id=None),
        Row(policy_id="p1", customer_id="c1", policy_type="Home", premium_amount=550.0,
            start_date=date(2023, 1, 1), end_date=date(2024, 1, 1), status_code=1,
            policy_version=2, renewal_of_policy_id="old"),
    ])


def test_dim_policy_scd2_has_two_rows(spark: SparkSession) -> None:
    from pipeline.gold.dimensions import build_dim_policy

    result = build_dim_policy(_make_policies(spark))
    assert result.count() == 2


def test_dim_policy_scd2_is_current_flag(spark: SparkSession) -> None:
    from pipeline.gold.dimensions import build_dim_policy

    rows = {r["policy_version"]: r for r in build_dim_policy(_make_policies(spark)).collect()}
    assert rows[2]["is_current"] is True
    assert rows[1]["is_current"] is False


def test_dim_policy_scd2_valid_to_on_v1(spark: SparkSession) -> None:
    from pipeline.gold.dimensions import build_dim_policy

    rows = {r["policy_version"]: r for r in build_dim_policy(_make_policies(spark)).collect()}
    assert rows[1]["valid_to"] == date(2023, 1, 1)  # next version's start_date
    assert rows[2]["valid_to"] is None               # current row: no valid_to


def test_dim_policy_policy_sk_is_unique(spark: SparkSession) -> None:
    from pipeline.gold.dimensions import build_dim_policy

    result = build_dim_policy(_make_policies(spark))
    sks = [r["policy_sk"] for r in result.collect()]
    assert len(sks) == len(set(sks))


def test_dim_date_row_count(spark: SparkSession) -> None:
    from pipeline.gold.dimensions import build_dim_date

    dim = build_dim_date(spark, "2023-01-01", "2023-01-31")
    assert dim.count() == 31


def test_dim_date_columns(spark: SparkSession) -> None:
    from pipeline.gold.dimensions import build_dim_date

    dim = build_dim_date(spark, "2023-03-15", "2023-03-15")
    row = dim.first()
    assert row["date_sk"] == 20230315
    assert row["year"] == 2023
    assert row["month"] == 3
    assert row["quarter"] == 1
