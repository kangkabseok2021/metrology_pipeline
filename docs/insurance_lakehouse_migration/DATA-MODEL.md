# Gold Layer — Data Model

## Star Schema

```
dim_date ──┐
           ├── fact_claims ──── dim_customer
dim_policy─┘                        │
           ├── fact_premiums    dim_customer_xref
dim_policy─┘
```

## Dimension Tables

### dim_policy (SCD Type 2)

| Column | Type | Notes |
|---|---|---|
| policy_sk | INT | Surrogate key (row_number by policy_id, policy_version) |
| policy_id | STRING | Natural key (GUID from policyadmin) |
| policy_version | INT | Version number; renewals increment this |
| policy_type | STRING | HomeContents / ThirdPartyLiability / VehicleComprehensive / Legal |
| premium_amount | DOUBLE | Annual premium in EUR |
| start_date | DATE | Policy start |
| end_date | DATE | Policy end |
| status_code | INT | 1=Active, 2=Lapsed, 3=Cancelled |
| valid_from | DATE | SCD2: start of this version |
| valid_to | DATE | SCD2: NULL for current row; next version's start_date otherwise |
| is_current | BOOLEAN | True only for the latest version per policy_id |

### dim_customer

| Column | Type | Notes |
|---|---|---|
| customer_sk | INT | Surrogate key |
| pa_customer_id | STRING | policyadmin GUID |
| claims_seq_id | INT | Maps to claims.customer_id |
| billing_email | STRING | Maps to billing.customer_email; NULL if no billing records |
| first_name, last_name, email, date_of_birth | STRING/DATE | From policyadmin Silver |

### dim_date

Standard date dimension — `date_sk` is `YYYYMMDD` integer, covering 2021-01-01 to 2024-12-31.

## Fact Tables

### fact_claims

| Column | Type | Notes |
|---|---|---|
| claim_sk | INT | Surrogate key |
| policy_sk | INT | FK → dim_policy (current row only) |
| customer_sk | INT | FK → dim_customer |
| date_sk | INT | FK → dim_date (event_date) |
| claim_id | INT | Natural key |
| claim_type | STRING | WaterDamage / Theft / Accident / FireDamage |
| status | STRING | open / closed / rejected |
| payout_amount | DOUBLE | NULL if no payout yet; negative if is_correction=True |
| is_correction | BOOLEAN | True for negative-payout correction rows |

### fact_premiums

| Column | Type | Notes |
|---|---|---|
| premium_sk | INT | Surrogate key |
| policy_sk | INT | FK → dim_policy (current) |
| date_sk | INT | FK → dim_date (invoice_date) |
| invoice_id | INT | Natural key |
| customer_email | STRING | Denormalised from billing (may be NULL) |
| amount | DOUBLE | Invoice amount in EUR |
| currency | STRING | Always EUR in this dataset |
| amount_paid | DOUBLE | NULL if no payment recorded |
| payment_method | STRING | DirectDebit / BankTransfer / CreditCard |

## Column Lineage (selected)

| Gold column | Silver source | Bronze source | Origin system |
|---|---|---|---|
| fact_claims.policy_sk | dim_policy.policy_sk | policyadmin.Policies.PolicyID | policyadmin |
| fact_claims.customer_sk | dim_customer.customer_sk | claims.claim_events.customer_id → xref | claims + policyadmin |
| fact_claims.payout_amount | claims.payouts.payout_amount | claims.payouts.payout_amount | claims |
| fact_premiums.amount | billing.invoices.amount | billing.invoices.amount | billing |
| dim_policy.valid_to | computed by SCD2 window | policyadmin.Policies.StartDate (next version) | policyadmin |
