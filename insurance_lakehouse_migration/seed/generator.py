"""Populate MS SQL Server source schemas with realistic P&C insurance data."""

from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy import create_engine, text

fake = Faker("de_DE")
random.seed(42)
Faker.seed(42)

CUSTOMERS = int(os.getenv("SEED_CUSTOMERS", "500"))
POLICY_MULT = float(os.getenv("SEED_POLICY_MULT", "1.6"))
CLAIM_RATE = float(os.getenv("SEED_CLAIM_RATE", "0.15"))
INV_MULT = float(os.getenv("SEED_INV_MULT", "4.0"))

POLICY_TYPES = ["HomeContents", "ThirdPartyLiability", "VehicleComprehensive", "Legal"]
CLAIM_TYPES = ["WaterDamage", "Theft", "Accident", "FireDamage"]
PAYMENT_METHODS = ["DirectDebit", "BankTransfer", "CreditCard"]
HORIZON_START = datetime(2021, 1, 1)
HORIZON_END = datetime(2024, 12, 31)


def _rand_date(start: datetime, end: datetime) -> datetime:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(0, delta)))


def _create_db(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("IF DB_ID('InsuranceDB') IS NULL CREATE DATABASE InsuranceDB"))


def _apply_schemas(conn, base_dir: str) -> None:
    for fname in ["01_policyadmin_schema.sql", "02_claims_schema.sql", "03_billing_schema.sql"]:
        with open(os.path.join(base_dir, "sql", fname)) as fh:
            for stmt in fh.read().split("GO"):
                stmt = stmt.strip()
                if stmt:
                    conn.execute(text(stmt))


def seed_policyadmin(conn) -> tuple[list[dict], list[dict]]:
    """Seed policyadmin schema. Returns (customers, policies)."""
    customers = []
    for _ in range(CUSTOMERS):
        customers.append(
            {
                "CustomerID": str(uuid.uuid4()),
                "FirstName": fake.first_name(),
                "LastName": fake.last_name(),
                "DateOfBirth": _rand_date(datetime(1950, 1, 1), datetime(2000, 1, 1)),
                "Email": fake.unique.email(),
                "CreatedAt": _rand_date(HORIZON_START, datetime(2023, 1, 1)),
            }
        )
    conn.execute(
        text(
            "INSERT INTO policyadmin.Customers"
            " (CustomerID, FirstName, LastName, DateOfBirth, Email, CreatedAt)"
            " VALUES (:CustomerID,:FirstName,:LastName,:DateOfBirth,:Email,:CreatedAt)"
        ),
        customers,
    )

    policies = []
    for c in customers:
        n = max(1, round(random.gauss(POLICY_MULT, 0.5)))
        prev = None
        for v in range(1, n + 1):
            start = _rand_date(HORIZON_START, datetime(2024, 6, 1))
            end = start + timedelta(days=365 * random.randint(1, 3))
            pid = str(uuid.uuid4())
            policies.append(
                {
                    "PolicyID": pid,
                    "CustomerID": c["CustomerID"],
                    "PolicyType": random.choice(POLICY_TYPES),
                    "PremiumAmount": round(random.uniform(200, 2000), 2),
                    "StartDate": start,
                    "EndDate": end,
                    "StatusCode": random.choices([1, 2, 3], weights=[7, 2, 1])[0],
                    "PolicyVersion": v,
                    "RenewalOfPolicyID": prev,
                }
            )
            prev = pid
    conn.execute(
        text(
            "INSERT INTO policyadmin.Policies"
            " (PolicyID,CustomerID,PolicyType,PremiumAmount,StartDate,EndDate,"
            "StatusCode,PolicyVersion,RenewalOfPolicyID)"
            " VALUES (:PolicyID,:CustomerID,:PolicyType,:PremiumAmount,:StartDate,:EndDate,"
            ":StatusCode,:PolicyVersion,:RenewalOfPolicyID)"
        ),
        policies,
    )

    cov_types = ["Building", "Contents", "Liability", "Legal"]
    coverages = []
    for p in policies:
        for ct in random.sample(cov_types, k=random.randint(1, 3)):
            coverages.append(
                {
                    "CoverageID": str(uuid.uuid4()),
                    "PolicyID": p["PolicyID"],
                    "CoverageType": ct,
                    "CoverageLimit": round(random.uniform(10_000, 500_000), 2),
                    "Deductible": random.choice([0, 250, 500, 1000]),
                }
            )
    conn.execute(
        text(
            "INSERT INTO policyadmin.Coverages"
            " (CoverageID,PolicyID,CoverageType,CoverageLimit,Deductible)"
            " VALUES (:CoverageID,:PolicyID,:CoverageType,:CoverageLimit,:Deductible)"
        ),
        coverages,
    )
    return customers, policies


def seed_claims(conn, customers: list[dict], policies: list[dict]) -> None:
    """claims.customer_id is the 1-based rank of customer ordered by CreatedAt."""
    rank = {
        c["CustomerID"]: i + 1
        for i, c in enumerate(sorted(customers, key=lambda x: x["CreatedAt"]))
    }
    events = []
    for p in policies:
        if random.random() > CLAIM_RATE:
            continue
        for _ in range(random.randint(1, 3)):
            start = p["StartDate"]
            end = min(p["EndDate"], HORIZON_END)
            if start >= end:
                continue
            events.append(
                {
                    "policy_id": p["PolicyID"],
                    "customer_id": rank[p["CustomerID"]],
                    "event_date": _rand_date(start, end).date(),
                    "claim_type": random.choice(CLAIM_TYPES),
                    "status": random.choices(["open", "closed", "rejected"], weights=[2, 6, 2])[0],
                }
            )
    if not events:
        return
    conn.execute(
        text(
            "INSERT INTO claims.claim_events"
            " (policy_id,customer_id,event_date,claim_type,status)"
            " VALUES (:policy_id,:customer_id,:event_date,:claim_type,:status)"
        ),
        events,
    )
    claim_ids = [
        r[0]
        for r in conn.execute(text("SELECT claim_id FROM claims.claim_events ORDER BY claim_id"))
    ]
    payouts = []
    for cid in claim_ids:
        payouts.append(
            {
                "claim_id": cid,
                "payout_date": _rand_date(HORIZON_START, HORIZON_END).date(),
                "payout_amount": round(random.uniform(100, 15_000), 2),
                "is_correction": False,
            }
        )
        if random.random() < 0.05:
            payouts.append(
                {
                    "claim_id": cid,
                    "payout_date": (
                        _rand_date(HORIZON_START, HORIZON_END) + timedelta(days=10)
                    ).date(),
                    "payout_amount": -round(random.uniform(10, 500), 2),
                    "is_correction": True,
                }
            )
    conn.execute(
        text(
            "INSERT INTO claims.payouts (claim_id,payout_date,payout_amount,is_correction)"
            " VALUES (:claim_id,:payout_date,:payout_amount,:is_correction)"
        ),
        payouts,
    )


def seed_billing(conn, customers: list[dict], policies: list[dict]) -> None:
    """billing.customer_email is the join key; dates in DD/MM/YYYY."""
    email_map = {c["CustomerID"]: c["Email"] for c in customers}
    invoices = []
    for p in policies:
        email = email_map[p["CustomerID"]]
        for i in range(max(1, round(random.gauss(INV_MULT, 1.0)))):
            inv_date = p["StartDate"] + timedelta(days=30 * i)
            due_date = inv_date + timedelta(days=14)
            invoices.append(
                {
                    "policy_id": p["PolicyID"],
                    "customer_email": email if random.random() > 0.05 else None,
                    "invoice_date": inv_date.strftime("%d/%m/%Y"),
                    "due_date": due_date.strftime("%d/%m/%Y"),
                    "amount": round(p["PremiumAmount"] / 12, 2),
                    "currency": "EUR",
                }
            )
    conn.execute(
        text(
            "INSERT INTO billing.invoices"
            " (policy_id,customer_email,invoice_date,due_date,amount,currency)"
            " VALUES (:policy_id,:customer_email,:invoice_date,:due_date,:amount,:currency)"
        ),
        invoices,
    )
    inv_ids = [
        r[0]
        for r in conn.execute(text("SELECT invoice_id FROM billing.invoices ORDER BY invoice_id"))
    ]
    payments = []
    for inv_id in random.sample(inv_ids, k=int(len(inv_ids) * 0.85)):
        payments.append(
            {
                "invoice_id": inv_id,
                "payment_date": _rand_date(HORIZON_START, HORIZON_END).strftime("%d/%m/%Y"),
                "amount_paid": round(random.uniform(50, 300), 2),
                "payment_method": random.choice(PAYMENT_METHODS),
            }
        )
    conn.execute(
        text(
            "INSERT INTO billing.payments (invoice_id,payment_date,amount_paid,payment_method)"
            " VALUES (:invoice_id,:payment_date,:amount_paid,:payment_method)"
        ),
        payments,
    )


def run_seed(conn_url: str | None = None, base_dir: str | None = None) -> None:
    url = conn_url or os.environ["MSSQL_URL"]
    root = base_dir or os.path.dirname(os.path.dirname(__file__))
    master_url = url.replace("InsuranceDB", "master")
    _create_db(create_engine(master_url))
    engine = create_engine(url)
    with engine.begin() as conn:
        _apply_schemas(conn, root)
        customers, policies = seed_policyadmin(conn)
        seed_claims(conn, customers, policies)
        seed_billing(conn, customers, policies)
    print(f"Seeded {CUSTOMERS} customers, {len(policies)} policies")


if __name__ == "__main__":
    run_seed()
