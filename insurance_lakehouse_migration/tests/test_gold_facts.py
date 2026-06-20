"""Tests for Gold-layer fact builders."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from pyspark.sql import Row, SparkSession
from pyspark.sql.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

sys.path.insert(0, str(Path(__file__).parents[1]))

_DIM_POLICY_SCHEMA = StructType([
    StructField("policy_sk", IntegerType(), False),
    StructField("policy_id", StringType(), True),
    StructField("policy_version", IntegerType(), True),
    StructField("is_current", BooleanType(), True),
    StructField("valid_from", DateType(), True),
    StructField("valid_to", DateType(), True),
])


def _make_dim_policy(spark: SparkSession):
    return spark.createDataFrame([
        Row(policy_sk=1, policy_id="p1", policy_version=1, is_current=True,
            valid_from=date(2022, 1, 1), valid_to=None),
    ], schema=_DIM_POLICY_SCHEMA)


def _make_dim_customer(spark: SparkSession):
    return spark.createDataFrame([
        Row(customer_sk=1, pa_customer_id="c1", claims_seq_id=1, billing_email="a@b.com",
            first_name="Anna", last_name="M", email="a@b.com", date_of_birth=date(1985, 1, 1)),
    ])


def _make_dim_date(spark: SparkSession):
    from pipeline.gold.dimensions import build_dim_date
    return build_dim_date(spark, "2022-01-01", "2024-12-31")


def test_fact_claims_joins_policy_and_customer(spark: SparkSession) -> None:
    from pipeline.gold.facts import build_fact_claims

    claims_silver = spark.createDataFrame([
        Row(claim_id=101, policy_id="p1", customer_id=1, event_date=date(2022, 6, 1),
            claim_type="Theft", status="closed"),
    ])
    payouts_silver = spark.createDataFrame([
        Row(payout_id=1, claim_id=101, payout_date=date(2022, 6, 10),
            payout_amount=5000.0, is_correction=False),
    ])
    result = build_fact_claims(
        claims_silver, payouts_silver, _make_dim_policy(spark),
        _make_dim_customer(spark), _make_dim_date(spark)
    )
    assert result.count() == 1
    row = result.first()
    assert row["policy_sk"] == 1
    assert row["customer_sk"] == 1
    assert row["payout_amount"] == 5000.0


def test_fact_claims_no_payout_is_null(spark: SparkSession) -> None:
    from pipeline.gold.facts import build_fact_claims

    claims_silver = spark.createDataFrame([
        Row(claim_id=200, policy_id="p1", customer_id=1, event_date=date(2022, 7, 1),
            claim_type="Fire", status="open"),
    ])
    empty_schema = StructType([
        StructField("claim_id", IntegerType()),
        StructField("payout_date", DateType()),
        StructField("payout_amount", DoubleType()),
        StructField("is_correction", BooleanType()),
    ])
    payouts_silver = spark.createDataFrame([], empty_schema)
    result = build_fact_claims(
        claims_silver, payouts_silver,
        _make_dim_policy(spark), _make_dim_customer(spark), _make_dim_date(spark)
    )
    row = result.first()
    assert row["payout_amount"] is None


def test_fact_premiums_joins_policy(spark: SparkSession) -> None:
    from pipeline.gold.facts import build_fact_premiums

    invoices = spark.createDataFrame([
        Row(invoice_id=1, policy_id="p1", customer_email="a@b.com",
            invoice_date=date(2022, 3, 1), due_date=date(2022, 3, 15),
            amount=120.0, currency="EUR"),
    ])
    payments = spark.createDataFrame([
        Row(payment_id=1, invoice_id=1, payment_date=date(2022, 3, 5),
            amount_paid=120.0, payment_method="DirectDebit"),
    ])
    result = build_fact_premiums(invoices, payments, _make_dim_policy(spark), _make_dim_date(spark))
    assert result.count() == 1
    row = result.first()
    assert row["policy_sk"] == 1
    assert row["amount_paid"] == 120.0
