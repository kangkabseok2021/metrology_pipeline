-- Date dimension: full spine from min to max shipment date
-- Uses PostgreSQL generate_series; no external macro dependency

WITH date_spine AS (
    SELECT
        gs::DATE AS full_date
    FROM GENERATE_SERIES(
        (SELECT MIN(ship_date) FROM {{ ref('stg_shipments') }}),
        (SELECT MAX(ship_date) FROM {{ ref('stg_shipments') }}),
        INTERVAL '1 day'
    ) AS gs
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['full_date']) }} AS date_id,
    full_date,
    EXTRACT(YEAR  FROM full_date)::INT AS year,
    EXTRACT(MONTH FROM full_date)::INT AS month,
    EXTRACT(DAY   FROM full_date)::INT AS day,
    TO_CHAR(full_date, 'Month')         AS month_name,
    EXTRACT(QUARTER FROM full_date)::INT AS quarter,
    EXTRACT(DOW FROM full_date)::INT    AS day_of_week,
    CASE WHEN EXTRACT(DOW FROM full_date) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend
FROM date_spine
