"""Silver-layer transform helpers: pure Python + PySpark per-table transforms."""

from __future__ import annotations

import re
from datetime import datetime

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


# ── Pure-Python helpers (no Spark) ────────────────────────────────────────────

def parse_ddmmyyyy(value: str | None) -> str | None:
    """Convert 'DD/MM/YYYY' → 'YYYY-MM-DD'. Returns None for blank/None."""
    if not value or not value.strip():
        return None
    return datetime.strptime(value.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")


def pascal_to_snake(name: str) -> str:
    """PascalCase or camelCase → snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return re.sub("([A-Z])([A-Z])", r"\1_\2", s2).lower()


# ── PySpark column rename ─────────────────────────────────────────────────────

def rename_columns_to_snake(df: DataFrame) -> DataFrame:
    """Return DataFrame with all columns renamed to snake_case."""
    for col in df.columns:
        snake = pascal_to_snake(col)
        if snake != col:
            df = df.withColumnRenamed(col, snake)
    return df


# ── Delta MERGE writer ────────────────────────────────────────────────────────

def merge_or_create(df: DataFrame, path: str, key_cols: list[str]) -> None:
    """MERGE if Delta table exists at path; otherwise write (first run)."""
    from delta.tables import DeltaTable
    from pyspark.errors import AnalysisException

    try:
        target = DeltaTable.forPath(df.sparkSession, path)
        condition = " AND ".join(f"t.{k} = s.{k}" for k in key_cols)
        (
            target.alias("t")
            .merge(df.alias("s"), condition)
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
    except AnalysisException:
        df.write.format("delta").mode("overwrite").save(path)


# ── Per-table Silver transforms ───────────────────────────────────────────────

def silver_policyadmin_customers(df: DataFrame) -> DataFrame:
    """Bronze policyadmin.Customers → snake_case columns, ISO date strings."""
    return (
        rename_columns_to_snake(df)
        .withColumn("date_of_birth", F.to_date(F.col("date_of_birth")))
        .withColumn("created_at", F.to_date(F.col("created_at")))
        .drop("_source_system", "_ingested_at")
    )


def silver_policyadmin_policies(df: DataFrame) -> DataFrame:
    """Bronze policyadmin.Policies → snake_case, ISO dates."""
    return (
        rename_columns_to_snake(df)
        .withColumn("start_date", F.to_date(F.col("start_date")))
        .withColumn("end_date", F.to_date(F.col("end_date")))
        .drop("_source_system", "_ingested_at")
    )


def silver_policyadmin_coverages(df: DataFrame) -> DataFrame:
    return rename_columns_to_snake(df).drop("_source_system", "_ingested_at")


def silver_claims_events(df: DataFrame) -> DataFrame:
    """Bronze claims.claim_events — already snake_case and ISO dates; strip audit cols."""
    return df.drop("_source_system", "_ingested_at")


def silver_claims_payouts(df: DataFrame) -> DataFrame:
    return df.drop("_source_system", "_ingested_at")


_parse_date_udf = F.udf(parse_ddmmyyyy)


def silver_billing_invoices(df: DataFrame) -> DataFrame:
    """Convert DD/MM/YYYY invoice_date and due_date → ISO date (NULL on invalid input)."""
    return (
        df
        .withColumn("invoice_date", F.try_to_date(F.col("invoice_date"), "dd/MM/yyyy"))
        .withColumn("due_date", F.try_to_date(F.col("due_date"), "dd/MM/yyyy"))
        .drop("_source_system", "_ingested_at")
    )


def silver_billing_payments(df: DataFrame) -> DataFrame:
    return (
        df
        .withColumn("payment_date", F.try_to_date(F.col("payment_date"), "dd/MM/yyyy"))
        .drop("_source_system", "_ingested_at")
    )
