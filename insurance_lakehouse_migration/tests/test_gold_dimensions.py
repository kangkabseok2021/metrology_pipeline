"""Tests for Gold-layer dimension builders."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

sys.path.insert(0, str(Path(__file__).parents[1]))

_POLICY_SCHEMA = StructType([
    StructField("policy_id", StringType()),
    StructField("customer_id", StringType()),
    StructField("policy_type", StringType()),
    StructField("premium_amount", DoubleType()),
    StructField("start_date", DateType()),
    StructField("end_date", DateType()),
    StructField("status_code", IntegerType()),
    StructField("policy_version", IntegerType()),
    StructField("renewal_of_policy_id", StringType()),
])


def _make_policies(spark: SparkSession):
    return spark.createDataFrame([
        (
            "p1", "c1", "Home", 500.0,
            date(2022, 1, 1), date(2023, 1, 1), 1, 1, None,
        ),
        (
            "p1", "c1", "Home", 550.0,
            date(2023, 1, 1), date(2024, 1, 1), 1, 2, "old",
        ),
    ], _POLICY_SCHEMA)


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
