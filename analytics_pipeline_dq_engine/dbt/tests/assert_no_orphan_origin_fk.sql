-- Singular test: zero fact rows with origin_location_id not in dim_locations
SELECT COUNT(*) AS orphan_count
FROM {{ ref('fact_shipments') }} f
WHERE f.origin_location_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM {{ ref('dim_locations') }} dl
      WHERE dl.location_id = f.origin_location_id
  )
HAVING COUNT(*) > 0
