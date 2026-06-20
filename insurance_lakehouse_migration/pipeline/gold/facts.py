"""Gold-layer fact builders: fact_claims and fact_premiums."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def build_fact_claims(
    claims_silver: DataFrame,
    payouts_silver: DataFrame,
    dim_policy: DataFrame,
    dim_customer: DataFrame,
    dim_date: DataFrame,
) -> DataFrame:
    """
    Join claim_events + payouts to dim_policy (current rows), dim_customer (by claims_seq_id),
    and dim_date (by event_date). fact_claims has one row per claim event.
    Payouts are aggregated first to avoid fan-out on correction records.
    """
    current_policies = dim_policy.filter(F.col("is_current")).select("policy_sk", "policy_id")

    payouts_agg = payouts_silver.groupBy("claim_id").agg(
        F.sum("payout_amount").alias("payout_amount"),
        F.max("is_correction").cast("boolean").alias("has_correction"),
    )

    return (
        claims_silver.alias("ce")
        .join(payouts_agg.alias("p"), F.col("ce.claim_id") == F.col("p.claim_id"), "left")
        .join(current_policies.alias("dp"), F.col("ce.policy_id") == F.col("dp.policy_id"), "left")
        .join(
            dim_customer.select("customer_sk", "claims_seq_id").alias("dc"),
            F.col("ce.customer_id") == F.col("dc.claims_seq_id"),
            "left",
        )
        .join(
            dim_date.select("date_sk", "date").alias("dd"),
            F.col("ce.event_date") == F.col("dd.date"),
            "left",
        )
        .select(
            F.row_number()
            .over(Window.orderBy("ce.claim_id"))
            .alias("claim_sk"),
            F.col("dp.policy_sk"),
            F.col("dc.customer_sk"),
            F.col("dd.date_sk"),
            F.col("ce.claim_id"),
            F.col("ce.claim_type"),
            F.col("ce.status"),
            F.col("p.payout_amount"),
            F.col("p.has_correction"),
        )
    )


def build_fact_premiums(
    invoices_silver: DataFrame,
    payments_silver: DataFrame,
    dim_policy: DataFrame,
    dim_date: DataFrame,
) -> DataFrame:
    """
    Join billing invoices + payments to dim_policy (current) and dim_date (by invoice_date).
    """
    current_policies = dim_policy.filter(F.col("is_current")).select("policy_sk", "policy_id")

    return (
        invoices_silver.alias("i")
        .join(
            payments_silver.select("invoice_id", "amount_paid", "payment_method").alias("p"),
            F.col("i.invoice_id") == F.col("p.invoice_id"),
            "left",
        )
        .join(current_policies.alias("dp"), F.col("i.policy_id") == F.col("dp.policy_id"), "left")
        .join(
            dim_date.select("date_sk", "date").alias("dd"),
            F.col("i.invoice_date") == F.col("dd.date"),
            "left",
        )
        .select(
            F.row_number().over(Window.orderBy("i.invoice_id")).alias("premium_sk"),
            F.col("dp.policy_sk"),
            F.col("dd.date_sk"),
            F.col("i.invoice_id"),
            F.col("i.customer_email"),
            F.col("i.amount"),
            F.col("i.currency"),
            F.col("p.amount_paid"),
            F.col("p.payment_method"),
        )
    )
