"""End-to-end Bronze → Silver → Gold pipeline runner."""

from __future__ import annotations

import os

from pipeline.bronze.extract import extract_all
from pipeline.gold.dimensions import build_dim_customer, build_dim_date, build_dim_policy
from pipeline.gold.facts import build_fact_claims, build_fact_premiums
from pipeline.silver.identity import build_customer_xref
from pipeline.silver.transforms import (
    merge_or_create,
    silver_billing_invoices,
    silver_billing_payments,
    silver_claims_events,
    silver_claims_payouts,
    silver_policyadmin_coverages,
    silver_policyadmin_customers,
    silver_policyadmin_policies,
)
from pipeline.spark_session import get_spark


def run_pipeline(
    jdbc_url: str | None = None,
    bronze_path: str = "./data/bronze",
    silver_path: str = "./data/silver",
    gold_path: str = "./data/gold",
) -> None:
    jdbc_url = jdbc_url or os.environ["JDBC_URL"]
    spark = get_spark(include_jdbc=True)

    # ── Bronze ──────────────────────────────────────────────────────────────
    print("Bronze: extracting source tables...")
    extract_all(spark, jdbc_url, bronze_path)

    # ── Silver ──────────────────────────────────────────────────────────────
    print("Silver: standardising and building xref...")

    def _read(schema: str, table: str):
        return spark.read.format("delta").load(f"{bronze_path}/{schema}/{table}")

    pa_customers = silver_policyadmin_customers(_read("policyadmin", "customers"))
    pa_policies = silver_policyadmin_policies(_read("policyadmin", "policies"))
    pa_coverages = silver_policyadmin_coverages(_read("policyadmin", "coverages"))
    cl_events = silver_claims_events(_read("claims", "claim_events"))
    cl_payouts = silver_claims_payouts(_read("claims", "payouts"))
    bi_invoices = silver_billing_invoices(_read("billing", "invoices"))
    bi_payments = silver_billing_payments(_read("billing", "payments"))
    xref = build_customer_xref(pa_customers, bi_invoices)

    merge_or_create(pa_customers, f"{silver_path}/policyadmin/customers", ["customer_id"])
    merge_or_create(
        pa_policies, f"{silver_path}/policyadmin/policies", ["policy_id", "policy_version"]
    )
    merge_or_create(pa_coverages, f"{silver_path}/policyadmin/coverages", ["coverage_id"])
    merge_or_create(cl_events, f"{silver_path}/claims/claim_events", ["claim_id"])
    merge_or_create(cl_payouts, f"{silver_path}/claims/payouts", ["payout_id"])
    merge_or_create(bi_invoices, f"{silver_path}/billing/invoices", ["invoice_id"])
    merge_or_create(bi_payments, f"{silver_path}/billing/payments", ["payment_id"])
    merge_or_create(xref, f"{silver_path}/xref/dim_customer_xref", ["pa_customer_id"])

    # ── Gold ────────────────────────────────────────────────────────────────
    print("Gold: building star schema...")
    dim_policy = build_dim_policy(pa_policies)
    dim_customer = build_dim_customer(pa_customers, xref)
    dim_date = build_dim_date(spark)
    fact_claims = build_fact_claims(cl_events, cl_payouts, dim_policy, dim_customer, dim_date)
    fact_premiums = build_fact_premiums(bi_invoices, bi_payments, dim_policy, dim_date)

    merge_key = {
        "dim_policy": ["policy_id", "policy_version"],
        "dim_customer": ["pa_customer_id"],
        "dim_date": ["date_sk"],
        "fact_claims": ["claim_id"],
        "fact_premiums": ["invoice_id"],
    }
    for name, df in [
        ("dim_policy", dim_policy),
        ("dim_customer", dim_customer),
        ("dim_date", dim_date),
        ("fact_claims", fact_claims),
        ("fact_premiums", fact_premiums),
    ]:
        merge_or_create(df, f"{gold_path}/{name}", merge_key[name])
        print(f"  {name}: {df.count()} rows")

    print("Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()
