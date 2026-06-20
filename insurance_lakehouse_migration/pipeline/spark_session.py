"""SparkSession factory for the insurance lakehouse pipeline."""

from __future__ import annotations

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession


def get_spark(app_name: str = "insurance_lakehouse", include_jdbc: bool = False) -> SparkSession:
    packages = []
    if include_jdbc:
        packages.append("com.microsoft.sqlserver:mssql-jdbc:12.4.2.jre11")

    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.enabled", "false")
    )
    if packages:
        builder = builder.config("spark.jars.packages", ",".join(packages))

    return configure_spark_with_delta_pip(builder).getOrCreate()
