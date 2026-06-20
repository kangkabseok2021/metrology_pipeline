# Cross-System Customer Identity Resolution

## The Problem

Three systems use three incompatible customer identifiers:

| System | Identifier type | Example |
|---|---|---|
| policyadmin | GUID string | `3f7a9b2e-...` |
| claims | Integer | `142` |
| billing | Email | `anna.mueller@example.de` |

## Deterministic Mapping Rule

**policyadmin ↔ claims:**
The Faker generator assigns `claims.customer_id` as the 1-based rank of the corresponding
policyadmin customer when customers are ordered by `CreatedAt ASC, CustomerID ASC`.

The Silver identity resolution recreates this rank with `ROW_NUMBER() OVER (ORDER BY created_at, customer_id)`
on the policyadmin Silver customers table — producing the same integer sequence as the seed generator.

**policyadmin ↔ billing:**
`policyadmin.Customers.Email` = `billing.invoices.customer_email` — direct email match.

## dim_customer_xref Schema

| Column | Type | Description |
|---|---|---|
| `xref_id` | INT | Surrogate key (row_number over pa_customer_id) |
| `pa_customer_id` | STRING | policyadmin GUID |
| `claims_seq_id` | INT | maps to claims.claim_events.customer_id |
| `billing_email` | STRING | maps to billing.invoices.customer_email; NULL if no billing record |

## Implementation

`pipeline/silver/identity.py::build_customer_xref(pa_customers_silver, billing_invoices_silver)`
