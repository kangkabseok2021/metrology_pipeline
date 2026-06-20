"""Shared SparkSession fixture (session-scoped — starts once per pytest run)."""

from __future__ import annotations

import os

import pytest
from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

# Java 17 is required: Hadoop 3.4.x bundled with PySpark 4.x calls Subject.getSubject()
# which was removed in Java 23+. Java 17 (LTS) is the correct target for PySpark 4.x.
_JAVA17_HOME = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
if os.path.isdir(_JAVA17_HOME) and not os.environ.get("JAVA_HOME"):
    os.environ["JAVA_HOME"] = _JAVA17_HOME


@pytest.fixture(scope="session")
def spark() -> SparkSession:  # type: ignore[misc]
    builder = (
        SparkSession.builder.appName("insurance_test")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .config("spark.jars.ivy", os.path.expanduser("~/.ivy2.5.2"))
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
    )
    session = configure_spark_with_delta_pip(builder).getOrCreate()
    yield session
    session.stop()
