"""Tests for cross-system customer identity resolution."""

from __future__ import annotations

import sys
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

_PA_CUSTOMER_SCHEMA = StructType([
    StructField("customer_id", StringType(), False),
    StructField("email", StringType(), True),
    StructField("created_at", StringType(), True),
    StructField("first_name", StringType(), True),
    StructField("last_name", StringType(), True),
    StructField("date_of_birth", StringType(), True),
])

_BILLING_INVOICE_SCHEMA = StructType([
    StructField("invoice_id", IntegerType(), False),
    StructField("policy_id", StringType(), True),
    StructField("customer_email", StringType(), True),
    StructField("invoice_date", StringType(), True),
    StructField("due_date", StringType(), True),
    StructField("amount", DoubleType(), True),
    StructField("currency", StringType(), True),
])


def test_xref_links_email_to_pa_customer(spark: SparkSession) -> None:
    from pipeline.silver.identity import build_customer_xref

    pa_customers = spark.createDataFrame([
        Row(customer_id="guid-1", email="alice@example.com", created_at="2022-01-01",
            first_name="Alice", last_name="Smith", date_of_birth="1985-01-01"),
        Row(customer_id="guid-2", email="bob@example.com", created_at="2022-02-01",
            first_name="Bob", last_name="Jones", date_of_birth="1990-01-01"),
    ], schema=_PA_CUSTOMER_SCHEMA)
    billing_invoices = spark.createDataFrame([
        Row(invoice_id=1, policy_id="p1", customer_email="alice@example.com",
            invoice_date=None, due_date=None, amount=100.0, currency="EUR"),
    ], schema=_BILLING_INVOICE_SCHEMA)
    xref = build_customer_xref(pa_customers, billing_invoices)
    rows = {r["pa_customer_id"]: r for r in xref.collect()}

    alice = rows["guid-1"]
    assert alice["billing_email"] == "alice@example.com"
    assert alice["claims_seq_id"] == 1  # alice has earlier created_at → rank 1

    bob = rows["guid-2"]
    assert bob["billing_email"] is None  # no billing row for bob
    assert bob["claims_seq_id"] == 2    # bob created later → rank 2


def test_xref_row_count_equals_pa_customers(spark: SparkSession) -> None:
    from pipeline.silver.identity import build_customer_xref

    pa = spark.createDataFrame([
        Row(customer_id=f"g{i}", email=f"u{i}@x.com", created_at=f"2022-0{i+1}-01",
            first_name="X", last_name="Y", date_of_birth="1990-01-01")
        for i in range(3)
    ], schema=_PA_CUSTOMER_SCHEMA)
    billing = spark.createDataFrame([
        Row(invoice_id=1, policy_id="p", customer_email="u0@x.com",
            invoice_date=None, due_date=None, amount=10.0, currency="EUR"),
    ], schema=_BILLING_INVOICE_SCHEMA)
    xref = build_customer_xref(pa, billing)
    assert xref.count() == 3  # one xref row per PA customer regardless of billing match
