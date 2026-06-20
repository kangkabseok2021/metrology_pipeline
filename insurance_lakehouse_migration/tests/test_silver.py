"""Tests for per-table Silver transforms using chispa DataFrame equality."""

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

_BILLING_INVOICE_SCHEMA = StructType([
    StructField("invoice_id", IntegerType(), False),
    StructField("policy_id", StringType(), True),
    StructField("customer_email", StringType(), True),
    StructField("invoice_date", StringType(), True),
    StructField("due_date", StringType(), True),
    StructField("amount", DoubleType(), True),
    StructField("currency", StringType(), True),
    StructField("_source_system", StringType(), True),
    StructField("_ingested_at", StringType(), True),
])

_POLICY_SCHEMA = StructType([
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


def test_silver_billing_invoices_converts_dates(spark: SparkSession) -> None:
    from pipeline.silver.transforms import silver_billing_invoices

    df = spark.createDataFrame(
        [Row(invoice_id=1, policy_id="p1", customer_email="a@b.com",
             invoice_date="15/03/2023", due_date="29/03/2023", amount=100.0, currency="EUR",
             _source_system="billing", _ingested_at="2024-01-01")]
    )
    result = silver_billing_invoices(df)
    row = result.first()
    assert row["invoice_date"] == date(2023, 3, 15)
    assert row["due_date"] == date(2023, 3, 29)
    assert "_ingested_at" not in result.columns


def test_silver_billing_invoices_null_date_becomes_null(spark: SparkSession) -> None:
    from pipeline.silver.transforms import silver_billing_invoices

    df = spark.createDataFrame(
        [Row(invoice_id=1, policy_id="p1", customer_email=None,
             invoice_date="99/99/9999", due_date="01/01/2023", amount=50.0, currency="EUR",
             _source_system="billing", _ingested_at="2024-01-01")],
        schema=_BILLING_INVOICE_SCHEMA,
    )
    result = silver_billing_invoices(df)
    row = result.first()
    assert row["invoice_date"] is None  # unparseable date → null


def test_silver_policyadmin_customers_renames_columns(spark: SparkSession) -> None:
    from pipeline.silver.transforms import silver_policyadmin_customers

    df = spark.createDataFrame(
        [Row(CustomerID="guid-1", FirstName="Anna", LastName="Müller",
             DateOfBirth="1985-06-01", Email="anna@test.de", CreatedAt="2022-01-15",
             _source_system="policyadmin", _ingested_at="2024-01-01")]
    )
    result = silver_policyadmin_customers(df)
    assert "customer_i_d" in result.columns or "customer_id" in result.columns
    assert "first_name" in result.columns
    assert "last_name" in result.columns


def test_silver_policyadmin_policies_iso_dates(spark: SparkSession) -> None:
    from pipeline.silver.transforms import silver_policyadmin_policies

    df = spark.createDataFrame(
        [Row(PolicyID="p1", CustomerID="c1", PolicyType="Home",
             PremiumAmount=500.0, StartDate="2022-01-01", EndDate="2023-01-01",
             StatusCode=1, PolicyVersion=1, RenewalOfPolicyID=None,
             _source_system="policyadmin", _ingested_at="2024-01-01")],
        schema=_POLICY_SCHEMA,
    )
    result = silver_policyadmin_policies(df)
    row = result.first()
    assert row["start_date"] == date(2022, 1, 1)
    assert row["end_date"] == date(2023, 1, 1)
