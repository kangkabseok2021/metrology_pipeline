"""Shared SparkSession fixture (session-scoped — starts once per pytest run)."""

from __future__ import annotations

import pytest
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark() -> SparkSession:  # type: ignore[misc]
    builder = (
        SparkSession.builder.appName("insurance_test")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
    )
    session = configure_spark_with_delta_pip(builder).getOrCreate()
    yield session
    session.stop()
