# Dispatch Metrics – Weekly Refresh Workflow

This document describes a lightweight weekly workflow to keep a consolidated **dispatch metrics** table refreshed, using two alternative approaches. It also includes the final SQL needed to populate the table with the structure expected for subsequent analysis.

---

## 1) Objectives

* Consolidate key signals from multiple sources into a single partitioned table.
* Refresh **every Monday** and ingest data for the **previous week** (relative to the current execution date `{{ds}}`).
* Provide a consistent structure for downstream analysis: top offenders, segmentation, and WoW comparisons.

---

## 2) Dynamic Date Window (Previous Week)

* Execution date: `{{ds}}` (e.g., the Monday the job runs).
* Target window: from `{{ds}} - 7 days` through `{{ds}} - 1 day` (inclusive), i.e., the full **previous Monday–Sunday**.
* This window is applied to the source partition (`datestr`) to extract only last week’s data.

---

## 3) Workflow – High‑Level Design

### Core tasks (common to both methods)

1. **Extract**: Read prior‑week partitions from the upstream sources using the dynamic date filter.
2. **Transform**: Join, compute distances (km), and compute **ATD** in minutes.
3. **Load**: Write into a partitioned consolidated table (partition key: `datestr`).
4. **Analyze**: Produce weekly analytics (top offenders, segmentation by key dimensions, WoW comparisons).
5. **Validate & Monitor**: Row‑count checks, freshness checks, and anomaly guardrails (e.g., ATD distribution shifts).
6. **Notify**: Post status to a channel (success/fail), attach basic metrics summary.


---

## 4) Method 1 – Kirby Table + Python Job (Every Monday)

**Overview**

* Create a Kirby table (example: `kirby.dispatch_metrics`).
* A scheduled Python job runs every Monday, queries last week’s data, and **appends** the new rows via Kirby’s API.

**Tasks**

1. **Create storage**: Provision `kirby.dispatch_metrics` with the target schema.
2. **Schedule**: Python job (cron/uworc/scheduler) set to Mondays 08:00 local.
3. **Query & Extract**: Use the dynamic `{{ds}}` window to pull last week’s data.
4. **Append via API**: Upsert/append to Kirby using its ingestion API.
5. **Post‑load checks**: Validate counts vs. upstream; sanity‑check ATD quartiles.


## 5) Method 2 – uWorc Scheduled SQL (Every Monday)

**Overview**

* Maintain a Hive/Parquet table (e.g., `tmp.dispatch_metrics`).
* A scheduled uWorc job runs a single SQL to **overwrite** last week’s partition(s) and then downstream Python reads from this table for analytics.

**Tasks**

1. **Create table**: Partitioned by `datestr`.
2. **Schedule**: uWorc job runs Mondays 08:00 local, with `{{ds}}` provided.
3. **Consolidation SQL**: Pulls and transforms last week’s data (see **Final SQL** below).
4. **Insert/Overwrite**: Writes only the relevant partitions.
5. **Quality checks** and **notifications** as in Method 1.


## 6) Final SQL (for Method 2)

> Use this SQL to create and refresh the weekly consolidated table. It expects an execution date `{{ds}}` (Monday) and loads data for the previous week.

```sql
-- Create metrics consolidation table
CREATE TABLE IF NOT EXISTS tmp.dispatch_metrics (
    territory                         STRING
  , country_name                      STRING
  , workflow_uuid                     STRING
  , driver_uuid                       STRING
  , delivery_trip_uuid                STRING
  , courier_flow                      STRING
  , restaurant_offered_timestamp_utc  TIMESTAMP
  , order_final_state_timestamp_local TIMESTAMP
  , eater_request_timestamp_local     TIMESTAMP
  , geo_archetype                     STRING
  , merchant_surface                  STRING
  , pickup_distance                   DOUBLE
  , dropoff_distance                  DOUBLE
  , ATD                               DOUBLE
)
PARTITIONED BY (
    -- Partition to refresh the pipeline in a weekly basis
    datestr STRING
)
STORED AS PARQUET;


-- Consolidate the data from the different data tables
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
        UNIX_TIMESTAMP(to_utc_timestamp(t4.order_final_state_timestamp, 'America/Mexico_City'))
        - UNIX_TIMESTAMP(t4.restaurant_offered_timestamp_utc)
      ) / 60.0 AS ATD
    , datestr
  FROM delivery_matching.eats_dispatch_metrics_job_message t3
  JOIN tmp.lea_trips_scope_atd_consolidation_v2 t4
    ON t3.workflowuuid = t4.workflow_uuid
  JOIN kirby_external_data.cities_strategy_region t2
    ON t3.cityid = t2.city_id
  JOIN dwh.dim_city t1
    ON t3.cityid = t1.city_id
  WHERE TRUE
    -- Dynamic date partition (pipeline runs every Monday → previous week)
    AND DATE(t3.datestr) BETWEEN DATE_SUB('{{ds}}', 7) AND DATE_SUB('{{ds}}', 1)
    -- Only Mexico
    AND t1.country_name = 'Mexico'
)

-- Insert (overwrite) the information for the target partitions
INSERT OVERWRITE TABLE tmp.dispatch_metrics
PARTITION (datestr)
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
  , datestr
FROM data_consolidation;
```

---

## 7) Downstream Analytics (Both Methods)

After the load, a Python or SQL analysis step should:

* **Filter top offenders** by agreed thresholds (e.g., top X% ATD, or absolute ATD > cutoff).
* **Segment** by: `territory`, `geo_archetype`, `courier_flow`, `merchant_surface`, **day of week**, **hour**.
* Produce **WoW comparisons** for key KPIs (median/avg ATD, counts, distances), highlighting material shifts.
* Optionally persist a weekly summary table/view for dashboards.

---

## 8) Validation & Monitoring

* **Freshness**: Confirm partitions exist for each day in the previous week.
* **Row counts**: Compare against moving average for the last 4 weeks (± tolerance).
* **Metric sanity**: ATD not negative; typical ranges stable; outlier share within band.
* **Alerts**: Failure or anomaly → notify with run ID, affected partitions, quick links to logs.

---

## 9) Security & Governance

* Principle of least privilege for write access.
* Data classification: confirm the table’s sensitivity level and abide by retention and sharing policies.
* Document lineage and owners for audits.

---

## 10) Success Criteria

* Table refreshed by **09:00 local** every Monday.
* No missing days in the prior week partition.
* Weekly summary report delivered (top offenders + WoW deltas).
* Zero manual interventions required in steady state.

