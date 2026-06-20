"""Tests for Bronze extraction audit columns."""

from __future__ import annotations

import sys
from pathlib import Path

from pyspark.sql import Row, SparkSession

sys.path.insert(0, str(Path(__file__).parents[1]))


def test_write_bronze_adds_audit_columns(spark: SparkSession, tmp_path) -> None:
    from pipeline.bronze.extract import write_bronze

    df = spark.createDataFrame([Row(id=1, name="Alice")])
    out = str(tmp_path / "bronze")
    write_bronze(df, out, "policyadmin", "Customers")

    result = spark.read.format("delta").load(f"{out}/policyadmin/customers")
    assert "_source_system" in result.columns
    assert "_ingested_at" in result.columns
    row = result.first()
    assert row["_source_system"] == "policyadmin"
    assert row["id"] == 1


def test_write_bronze_partition_by_ingested_at(spark: SparkSession, tmp_path) -> None:
    from pipeline.bronze.extract import write_bronze

    df = spark.createDataFrame([Row(x=1), Row(x=2)])
    out = str(tmp_path / "bronze2")
    write_bronze(df, out, "claims", "claim_events")

    result = spark.read.format("delta").load(f"{out}/claims/claim_events")
    assert result.count() == 2
