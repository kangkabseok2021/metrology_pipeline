-- Product dimension: SKU → category + weight_class

WITH skus AS (
    SELECT DISTINCT product_sku FROM {{ ref('stg_shipments') }}
),

enriched AS (
    SELECT
        product_sku,
        CASE
            WHEN CAST(REPLACE(product_sku, 'SKU-', '') AS INT) BETWEEN 1  AND 5  THEN 'Electronics'
            WHEN CAST(REPLACE(product_sku, 'SKU-', '') AS INT) BETWEEN 6  AND 10 THEN 'Machinery'
            WHEN CAST(REPLACE(product_sku, 'SKU-', '') AS INT) BETWEEN 11 AND 15 THEN 'Chemicals'
            ELSE 'Consumables'
        END AS category,
        CASE
            WHEN CAST(REPLACE(product_sku, 'SKU-', '') AS INT) BETWEEN 1  AND 7  THEN 'Light'
            WHEN CAST(REPLACE(product_sku, 'SKU-', '') AS INT) BETWEEN 8  AND 14 THEN 'Medium'
            ELSE 'Heavy'
        END AS weight_class
    FROM skus
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['product_sku']) }} AS product_id,
    product_sku,
    category,
    weight_class
FROM enriched
