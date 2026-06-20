"""Bronze-layer extraction: JDBC → Delta with audit columns."""

from __future__ import annotations

from datetime import datetime, UTC

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def extract_table(
    spark: SparkSession,
    jdbc_url: str,
    jdbc_properties: dict,
    schema: str,
    table: str,
) -> DataFrame:
    """Read one table from MS SQL Server via JDBC."""
    return spark.read.jdbc(
        url=jdbc_url,
        table=f"{schema}.{table}",
        properties=jdbc_properties,
    )


def write_bronze(df: DataFrame, bronze_path: str, schema: str, table: str) -> None:
    """Append audit columns and write to Delta Bronze (full overwrite)."""
    ingested_at = datetime.now(UTC).strftime("%Y-%m-%d")
    (
        df.withColumn("_source_system", F.lit(schema))
        .withColumn("_ingested_at", F.lit(ingested_at))
        .write.format("delta")
        .mode("overwrite")
        .partitionBy("_ingested_at")
        .save(f"{bronze_path}/{schema}/{table.lower()}")
    )


def extract_all(
    spark: SparkSession,
    jdbc_url: str,
    bronze_path: str,
    sa_password: str = "Str0ngP@ssw0rd!",
) -> None:
    """Extract all 7 source tables into Bronze Delta."""
    props = {
        "user": "sa",
        "password": sa_password,
        "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
    }
    tables = {
        "policyadmin": ["Customers", "Policies", "Coverages"],
        "claims": ["claim_events", "payouts"],
        "billing": ["invoices", "payments"],
    }
    for schema, tbl_list in tables.items():
        for table in tbl_list:
            df = extract_table(spark, jdbc_url, props, schema, table)
            write_bronze(df, bronze_path, schema, table)
            print(f"  Bronze: {schema}.{table} → {df.count()} rows")
