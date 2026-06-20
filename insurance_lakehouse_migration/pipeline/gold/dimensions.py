"""Gold-layer dimension builders."""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def build_dim_policy(policies_silver: DataFrame) -> DataFrame:
    """
    SCD Type 2 for dim_policy: one row per (policy_id, policy_version).
    valid_from = start_date of this version
    valid_to   = start_date of the next version (NULL for the current row)
    is_current = True only on the latest version per policy_id
    policy_sk  = deterministic surrogate key (row_number ordered by policy_id, policy_version)
    """
    w_by_version = Window.partitionBy("policy_id").orderBy("policy_version")
    w_global = Window.orderBy("policy_id", "policy_version")

    return (
        policies_silver.withColumn("valid_from", F.col("start_date"))
        .withColumn("valid_to", F.lead("start_date", 1).over(w_by_version))
        .withColumn("is_current", F.lead("policy_version", 1).over(w_by_version).isNull())
        .withColumn("policy_sk", F.row_number().over(w_global))
    )


def build_dim_customer(customers_silver: DataFrame, xref: DataFrame) -> DataFrame:
    """
    One consolidated row per policyadmin customer, enriched with xref identity fields.
    customer_sk = deterministic surrogate (row_number by pa_customer_id)
    """
    return (
        customers_silver.alias("c")
        .join(xref.alias("x"), F.col("c.customer_id") == F.col("x.pa_customer_id"), "left")
        .select(
            F.row_number()
            .over(Window.orderBy("c.customer_id"))
            .alias("customer_sk"),
            F.col("c.customer_id").alias("pa_customer_id"),
            F.col("x.billing_email"),
            F.col("x.claims_seq_id"),
            F.col("c.first_name"),
            F.col("c.last_name"),
            F.col("c.email"),
            F.col("c.date_of_birth"),
        )
    )


def build_dim_date(
    spark: SparkSession, start: str = "2021-01-01", end: str = "2024-12-31"
) -> DataFrame:
    """Generate a date dimension covering every day from start to end (inclusive)."""
    seq_sql = (
        f"SELECT explode(sequence("
        f"to_date('{start}'), to_date('{end}'), interval 1 day)) AS date"
    )
    return (
        spark.sql(seq_sql)
        .select(
            F.date_format(F.col("date"), "yyyyMMdd").cast("int").alias("date_sk"),
            F.col("date"),
            F.year(F.col("date")).alias("year"),
            F.month(F.col("date")).alias("month"),
            F.quarter(F.col("date")).alias("quarter"),
            F.dayofweek(F.col("date")).alias("day_of_week"),
            F.date_format(F.col("date"), "MMMM").alias("month_name"),
        )
    )
