-- Singular test: zero fact rows with product_id not in dim_products
SELECT COUNT(*) AS orphan_count
FROM {{ ref('fact_shipments') }} f
WHERE f.product_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM {{ ref('dim_products') }} dp
      WHERE dp.product_id = f.product_id
  )
HAVING COUNT(*) > 0
