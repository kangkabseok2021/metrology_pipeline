# Legacy Source Systems — Landscape Documentation

Three independent MS SQL Server schemas represent separate legacy applications with deliberately
inconsistent data conventions — motivating the Bronze→Silver consolidation work.

## policyadmin (Policy Administration System)

**Customer identifier:** GUID (`CustomerID UNIQUEIDENTIFIER`)
**Column style:** PascalCase (`FirstName`, `PolicyType`, `PremiumAmount`)
**Date format:** DATETIME (ISO-compatible via JDBC)
**Notable quirk:** Policies are versioned — a renewal creates a new `Policies` row with
`PolicyVersion + 1` and `RenewalOfPolicyID` pointing to the predecessor. The Silver SCD2
transform must detect these version chains.

```
policyadmin.Customers  ──< policyadmin.Policies ──< policyadmin.Coverages
```

## claims (Claims Management System)

**Customer identifier:** INT (`customer_id`) — 1-based rank of customer by `CreatedAt` in policyadmin.
This is the cross-system inconsistency: claims uses a sequential integer while policyadmin uses GUIDs.
See `IDENTITY-RESOLUTION.md` for the deterministic mapping rule.
**Column style:** snake_case
**Date format:** ISO DATE (no conversion needed)

```
claims.claim_events ──< claims.payouts
```

## billing (Billing & Invoice System)

**Customer identifier:** `customer_email NVARCHAR(255)` — 5% of rows intentionally NULL.
**Column style:** snake_case
**Date format:** `DD/MM/YYYY` string (non-ISO) — must be converted in the Silver layer.

```
billing.invoices ──< billing.payments
```

## Known Cross-System Inconsistencies

| Issue | Source | Silver Resolution |
|---|---|---|
| Customer ID format mismatch | policyadmin GUID vs claims INT vs billing email | `dim_customer_xref` (see IDENTITY-RESOLUTION.md) |
| Date format mismatch | billing DD/MM/YYYY vs policyadmin DATETIME | `F.to_date(col, 'dd/MM/yyyy')` in silver_billing_invoices |
| Column naming mismatch | policyadmin PascalCase vs claims/billing snake_case | `rename_columns_to_snake()` |
| Missing customer email | billing.invoices — 5% NULL | Left join; NULL billing_email in xref is acceptable |
| Negative payout corrections | claims.payouts.is_correction = True | Preserved in Gold; filtered in analytics views |
