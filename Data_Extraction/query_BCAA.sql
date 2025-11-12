WITH data_consolidation AS (
  SELECT
      t2.territory
    , t1.country_name
    , t4.workflow_uuid
    , t4.driver_uuid
    , t4.delivery_trip_uuid
    , t4.courier_flow
    , t4.restaurant_offered_timestamp_utc
    , t4.order_final_state_timestamp_local
    , t4.eater_request_timestamp_local
    , t4.geo_archetype
    , t4.merchant_surface
    , t3.pickupdistance / 1000.0 AS pickup_distance
    , t3.traveldistance / 1000.0 AS dropoff_distance
    , (
        to_unixtime( (t4.order_final_state_timestamp AT TIME ZONE 'America/Mexico_City') )
        - to_unixtime( t4.restaurant_offered_timestamp_utc )
      ) / 60.0 AS ATD
    , t3.datestr
  FROM delivery_matching.eats_dispatch_metrics_job_message t3
  JOIN tmp.lea_trips_scope_atd_consolidation_v2 t4
    ON t3.workflowuuid = t4.workflow_uuid
  JOIN kirby_external_data.cities_strategy_region t2
    ON t3.cityid = t2.city_id
  JOIN dwh.dim_city t1
    ON t3.cityid = t1.city_id
  WHERE TRUE
    -- Ventana dinámica (pipeline corre los lunes): últimos 7 días hasta ayer respecto a {{ds}}
    AND CAST(t3.datestr AS DATE)
        BETWEEN date_add('day', -7, CAST('{{ds}}' AS DATE))
            AND date_add('day', -1, CAST('{{ds}}' AS DATE))
    -- Solo México
    AND t1.country_name = 'Mexico'
)

SELECT
    territory
  , country_name
  , workflow_uuid
  , driver_uuid
  , delivery_trip_uuid
  , courier_flow
  , restaurant_offered_timestamp_utc
  , order_final_state_timestamp_local
  , eater_request_timestamp_local
  , geo_archetype
  , merchant_surface
  , pickup_distance
  , dropoff_distance
  , ATD
FROM data_consolidation;
