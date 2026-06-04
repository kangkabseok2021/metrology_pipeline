-- Location dimension: hub → region + country lookup

WITH hubs AS (
    SELECT DISTINCT origin_hub AS hub_code FROM {{ ref('stg_shipments') }}
    UNION
    SELECT DISTINCT destination_hub FROM {{ ref('stg_shipments') }}
),

enriched AS (
    SELECT
        hub_code,
        CASE hub_code
            WHEN 'NYC' THEN 'Northeast'  WHEN 'LAX' THEN 'West'
            WHEN 'CHI' THEN 'Midwest'    WHEN 'HOU' THEN 'South'
            WHEN 'PHX' THEN 'Southwest'  WHEN 'PHI' THEN 'Northeast'
            WHEN 'SAN' THEN 'West'       WHEN 'DAL' THEN 'South'
            WHEN 'SJC' THEN 'West'       WHEN 'AUS' THEN 'South'
            WHEN 'LHR' THEN 'North'      WHEN 'CDG' THEN 'West'
            WHEN 'FRA' THEN 'West'       WHEN 'AMS' THEN 'West'
            WHEN 'MAD' THEN 'South'      WHEN 'BCN' THEN 'South'
            WHEN 'MXP' THEN 'North'      WHEN 'ZRH' THEN 'Central'
            WHEN 'VIE' THEN 'East'       WHEN 'BRU' THEN 'West'
            ELSE 'Unknown'
        END AS region,
        CASE hub_code
            WHEN 'NYC' THEN 'USA' WHEN 'LAX' THEN 'USA'
            WHEN 'CHI' THEN 'USA' WHEN 'HOU' THEN 'USA'
            WHEN 'PHX' THEN 'USA' WHEN 'PHI' THEN 'USA'
            WHEN 'SAN' THEN 'USA' WHEN 'DAL' THEN 'USA'
            WHEN 'SJC' THEN 'USA' WHEN 'AUS' THEN 'USA'
            WHEN 'LHR' THEN 'GBR' WHEN 'CDG' THEN 'FRA'
            WHEN 'FRA' THEN 'DEU' WHEN 'AMS' THEN 'NLD'
            WHEN 'MAD' THEN 'ESP' WHEN 'BCN' THEN 'ESP'
            WHEN 'MXP' THEN 'ITA' WHEN 'ZRH' THEN 'CHE'
            WHEN 'VIE' THEN 'AUT' WHEN 'BRU' THEN 'BEL'
            ELSE 'UNK'
        END AS country_code
    FROM hubs
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['hub_code']) }} AS location_id,
    hub_code,
    region,
    country_code
FROM enriched
