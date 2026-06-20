"""Cross-system customer identity resolution: policyadmin ↔ billing ↔ claims."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def build_customer_xref(
    pa_customers: DataFrame,
    billing_invoices: DataFrame,
) -> DataFrame:
    """
    Build dim_customer_xref linking three identity spaces:
      - pa_customer_id: GUID string from policyadmin.Customers
      - claims_seq_id : 1-based rank by created_at (matches claims.claim_events.customer_id INT)
      - billing_email : customer_email from billing.invoices (NULL if no billing match)

    Returns one row per policyadmin customer.
    """
    billing_emails = billing_invoices.select(F.col("customer_email")).distinct()

    # Add claims_seq_id rank first, then alias the result for the join
    pa_with_rank = pa_customers.withColumn(
        "claims_seq_id",
        F.row_number().over(Window.orderBy("created_at", "customer_id")),
    )

    return (
        pa_with_rank.alias("pa")
        .join(billing_emails.alias("b"), F.col("pa.email") == F.col("b.customer_email"), "left")
        .select(
            F.row_number().over(Window.orderBy(F.col("pa.customer_id"))).alias("xref_id"),
            F.col("pa.customer_id").alias("pa_customer_id"),
            F.col("pa.claims_seq_id"),
            F.col("b.customer_email").alias("billing_email"),
        )
    )
