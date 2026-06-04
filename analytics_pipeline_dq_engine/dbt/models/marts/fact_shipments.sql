-- Fact table: shipments joined to all three dimensions
-- LEFT JOIN preserves nulls so referential failures surface in dbt tests

WITH stg AS (
    SELECT * FROM {{ ref('stg_shipments') }}
),

dl_origin AS (
    SELECT location_id, hub_code FROM {{ ref('dim_locations') }}
),

dl_dest AS (
    SELECT location_id, hub_code FROM {{ ref('dim_locations') }}
),

dd AS (
    SELECT date_id, full_date FROM {{ ref('dim_dates') }}
),

dp AS (
    SELECT product_id, product_sku FROM {{ ref('dim_products') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['stg.shipment_id']) }} AS shipment_sk,
    stg.shipment_id,
    o.location_id   AS origin_location_id,
    d.location_id   AS destination_location_id,
    dd.date_id      AS ship_date_id,
    dp.product_id,
    stg.carrier,
    stg.weight_kg,
    stg.quantity,
    stg.shipping_cost_usd
FROM stg
LEFT JOIN dl_origin  o  ON stg.origin_hub      = o.hub_code
LEFT JOIN dl_dest    d  ON stg.destination_hub = d.hub_code
LEFT JOIN dd             ON stg.ship_date       = dd.full_date
LEFT JOIN dp             ON stg.product_sku     = dp.product_sku
