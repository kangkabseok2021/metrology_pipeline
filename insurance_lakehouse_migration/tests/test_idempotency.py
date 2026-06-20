"""Verify Delta MERGE produces identical output on second run (idempotency)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from pyspark.sql import Row, SparkSession
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

sys.path.insert(0, str(Path(__file__).parents[1]))

_BRONZE_POLICY_SCHEMA = StructType([
    StructField("PolicyID", StringType(), True),
    StructField("CustomerID", StringType(), True),
    StructField("PolicyType", StringType(), True),
    StructField("PremiumAmount", DoubleType(), True),
    StructField("StartDate", StringType(), True),
    StructField("EndDate", StringType(), True),
    StructField("StatusCode", IntegerType(), True),
    StructField("PolicyVersion", IntegerType(), True),
    StructField("RenewalOfPolicyID", StringType(), True),
    StructField("_source_system", StringType(), True),
    StructField("_ingested_at", StringType(), True),
])


def test_silver_merge_is_idempotent(spark: SparkSession, tmp_path) -> None:
    from pipeline.silver.transforms import merge_or_create, silver_policyadmin_policies

    bronze_data = [
        Row(PolicyID="p1", CustomerID="c1", PolicyType="Home",
            PremiumAmount=500.0, StartDate="2022-01-01", EndDate="2023-01-01",
            StatusCode=1, PolicyVersion=1, RenewalOfPolicyID=None,
            _source_system="policyadmin", _ingested_at="2024-01-01"),
    ]
    bronze_df = spark.createDataFrame(bronze_data, schema=_BRONZE_POLICY_SCHEMA)
    path = str(tmp_path / "silver_policies")

    # Run 1 — PolicyID → policy_i_d after pascal_to_snake
    silver1 = silver_policyadmin_policies(bronze_df)
    merge_or_create(silver1, path, ["policy_i_d", "policy_version"])

    # Run 2 (identical input)
    silver2 = silver_policyadmin_policies(bronze_df)
    merge_or_create(silver2, path, ["policy_i_d", "policy_version"])

    result = spark.read.format("delta").load(path)
    assert result.count() == 1  # MERGE must not insert duplicates


def test_dim_policy_stable_sks_across_runs(spark: SparkSession) -> None:
    from pipeline.gold.dimensions import build_dim_policy

    policies = spark.createDataFrame([
        Row(policy_id="p1", customer_id="c1", policy_type="Home", premium_amount=500.0,
            start_date=date(2022, 1, 1), end_date=date(2023, 1, 1), status_code=1,
            policy_version=1, renewal_of_policy_id=None),
        Row(policy_id="p1", customer_id="c1", policy_type="Home", premium_amount=550.0,
            start_date=date(2023, 1, 1), end_date=date(2024, 1, 1), status_code=1,
            policy_version=2, renewal_of_policy_id="old"),
    ])
    run1_sks = sorted([r["policy_sk"] for r in build_dim_policy(policies).collect()])
    run2_sks = sorted([r["policy_sk"] for r in build_dim_policy(policies).collect()])
    assert run1_sks == run2_sks  # deterministic row_number → same SKs
