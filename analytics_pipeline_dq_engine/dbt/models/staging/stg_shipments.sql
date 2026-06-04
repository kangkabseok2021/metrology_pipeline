-- Silver staging: cleans all quality issues from bronze.raw_shipments
-- Handles: mixed date formats, whitespace hub codes, negative costs, duplicates

WITH raw AS (
    SELECT * FROM {{ source('bronze', 'raw_shipments') }}
),

cleaned AS (
    SELECT
        shipment_id,

        -- Normalise whitespace + case in hub codes
        TRIM(UPPER(origin_hub))      AS origin_hub,
        TRIM(UPPER(destination_hub)) AS destination_hub,

        product_sku,
        carrier,

        -- Resolve mixed date formats: MM/DD/YYYY and YYYY-MM-DD
        CASE
            WHEN ship_date LIKE '__/__/____'
                THEN TO_DATE(ship_date, 'MM/DD/YYYY')
            ELSE TO_DATE(ship_date, 'YYYY-MM-DD')
        END AS ship_date,

        CAST(weight_kg   AS NUMERIC(10, 2)) AS weight_kg,
        CAST(quantity    AS INTEGER)         AS quantity,

        -- Nullify negative shipping costs (invalid)
        CASE
            WHEN CAST(shipping_cost_usd AS NUMERIC(12, 2)) < 0 THEN NULL
            ELSE CAST(shipping_cost_usd AS NUMERIC(12, 2))
        END AS shipping_cost_usd

    FROM raw
    WHERE shipment_id IS NOT NULL
),

-- Deduplicate: keep one row per shipment key, prefer non-null cost
deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY origin_hub, destination_hub, product_sku, carrier, ship_date
            ORDER BY shipping_cost_usd NULLS LAST
        ) AS rn
    FROM cleaned
)

SELECT
    shipment_id, origin_hub, destination_hub,
    product_sku, carrier, ship_date,
    weight_kg, quantity, shipping_cost_usd
FROM deduped
WHERE rn = 1
