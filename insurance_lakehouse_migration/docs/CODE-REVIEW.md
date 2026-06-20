# Code Review Checklist — Notebook & Pipeline PRs

## For every PR touching a Silver or Gold notebook

- [ ] **Schema change impact:** If a Silver column is added/renamed, does the Gold layer that reads it need updating? Check `pipeline/gold/dimensions.py` and `pipeline/gold/facts.py`.
- [ ] **MERGE key correctness:** If a new Silver table uses `merge_or_create`, are the `key_cols` the correct natural keys (not surrogate keys)?
- [ ] **Surrogate key determinism:** New `row_number()` calls must use a `Window.orderBy(...)` with a fully deterministic sort order (no ties). Add a tiebreaker column if needed.
- [ ] **Date format coverage:** If a new source column contains dates, confirm the Silver transform uses `F.to_date(col, 'dd/MM/yyyy')` (billing) or `F.to_date(col)` (policyadmin) as appropriate.
- [ ] **Quality suite:** If a new fact table FK column is added, add a null-check and referential-integrity check to `quality/suite.py::validate_gold_tables`.
- [ ] **Lineage diagram updated:** `docs/DATA-MODEL.md` column lineage table reflects the new column.
- [ ] **Tests pass offline:** `uv run pytest tests/ -m "not integration"` is green before merge.

## For PRs touching `seed/generator.py`

- [ ] The `claims_seq_id` mapping rule still matches: `ROW_NUMBER() OVER (ORDER BY created_at, customer_id)` in `pipeline/silver/identity.py` produces the same rank as the generator's `sorted(customers, key=lambda x: x["CreatedAt"])`.
- [ ] `SEED_CUSTOMERS` env var is respected; default stays 500 for fast local dev.
