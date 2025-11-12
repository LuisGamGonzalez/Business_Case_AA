"""
Streamlit dashboard centered on ATD with robust filters and KPIs.
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt  # used for scatter & histogram

from utils import (
    add_derived_fields,
    filter_frame,
    kpi_series,
    resolve_columns,
    agg_by,
    bar_chart,
    dual_axis_daily,
    ATD_COLOR,
    TRIPS_COLOR,
)

# ---------- Page config ----------
st.set_page_config(
    page_title="ATD Dashboard",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Mode selector (Tutorial / Dashboard)
st.sidebar.header("Mode")
mode = st.sidebar.selectbox("Select mode", ["Tutorial", "Dashboard"])


# ---------------- Tutorial page ---------------- #
if mode == "Tutorial":
    st.title("Welcome to the ATD Dashboard")
    st.markdown(
        """
**What you’ll find**
- KPIs: **Trips**, **ATD Mean**.
- Visuals by segmentation: **Territory**, **Geo Archetype**, **Courier Flow**, **Merchant Surface**.
- Temporal breakdown: **Day of week** (Mon→Sun), **Hour of day** (0→23), **Weekend vs Weekday**.
- Daily time series with **two axes**: ATD (left) and Trips (right).

**Color legend**
- 🟩 **ATD** — `#03c167`
- 🟨 **Trips** — `#ffc043`

**How to use filters**
1. Choose the **dataset** in the sidebar (Data Complete / Without outliers).
2. Apply filters for **Territory**, **Geo Archetype**, **Courier Flow**, **Merchant Surface**.
3. Narrow the **date range** and **pickup/dropoff distance** ranges.
4. Charts update automatically.

**Reading the charts**
- ATD bars 🟩 show **only the ATD value** as a label (white, dark-mode friendly).
- Trips bars 🟨 show **the trips count** as a label.
- Daily line chart: **green line** for ATD, **yellow line** for Trips, **independent y-axes**.
        """
    )
    st.stop()  # do not render filters/charts in Tutorial mode

# =================== DASHBOARD MODE ===================
st.sidebar.header("Data")

# Dataset paths (adjust as needed)
DATA_SOURCES = {
    "Data Complete": "/mnt/cephfs/hadoop-compute/phoenix/jose.luis.gonzalez/BCAA/data_complete.csv",
    "Data without outliers": "/mnt/cephfs/hadoop-compute/phoenix/jose.luis.gonzalez/BCAA/data_without_outliers.csv",
}
dataset_choice = st.sidebar.selectbox("Select dataset", list(DATA_SOURCES.keys()))
data_path = DATA_SOURCES[dataset_choice]

if not os.path.exists(data_path):
    st.error(f"File not found: {data_path}")
    st.stop()

df = pd.read_csv(data_path)

# ---------------- Preprocessing ---------------- #
cols = resolve_columns(df)
df = add_derived_fields(df, cols)

# Derive temporal columns if missing
if "_eater_request_dt" in df.columns:
    dt = pd.to_datetime(df["_eater_request_dt"], errors="coerce")
    if "hour_of_day" not in df.columns:
        df["hour_of_day"] = dt.dt.hour
    if "day_of_week" not in df.columns:
        df["day_of_week"] = dt.dt.dayofweek  # 0=Mon..6=Sun
    if "is_weekend" not in df.columns:
        df["is_weekend"] = dt.dt.dayofweek >= 5
# ---------------- Filters ---------------- #
st.sidebar.header("Filters")


def multiselect_for(col_key: str, label: str) -> Optional[List[str]]:
    col = cols.get(col_key)
    if not col:
        return None
    options = sorted([x for x in df[col].dropna().unique().tolist()])
    return st.sidebar.multiselect(label, options, default=options)


territory = multiselect_for("territory", "Territory")
geo_arch = multiselect_for("geo_archetype", "Geo archetype")
courier_flow = multiselect_for("courier_flow", "Courier flow")
merchant_surface = multiselect_for("merchant_surface", "Merchant surface")

# Date range
date_col = "_eater_request_dt"
if df[date_col].notna().any():
    min_dt = pd.to_datetime(df[date_col].min())
    max_dt = pd.to_datetime(df[date_col].max())
    date_range: Tuple[pd.Timestamp, pd.Timestamp] = st.sidebar.date_input(
        "Date range (Eater request)",
        value=(min_dt, max_dt),
        min_value=min_dt.to_pydatetime(),
        max_value=max_dt.to_pydatetime(),
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_ts = pd.to_datetime(date_range[0])
        end_ts = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
        date_range = (start_ts, end_ts)
    else:
        date_range = (min_dt, max_dt)
else:
    date_range = None

# Distance ranges (true min/max)
pickup_col = cols.get("pickup_distance")
dropoff_col = cols.get("dropoff_distance")

pickup_range = None
dropoff_range = None

if pickup_col:
    pmin, pmax = df[pickup_col].min(), df[pickup_col].max()
    pickup_range = st.sidebar.slider(
        "Pickup distance",
        min_value=float(np.floor(pmin)),
        max_value=float(np.ceil(pmax)),
        value=(float(np.floor(pmin)), float(np.ceil(pmax))),
        step=0.1,
    )

if dropoff_col:
    dmin, dmax = df[dropoff_col].min(), df[dropoff_col].max()
    dropoff_range = st.sidebar.slider(
        "Dropoff distance",
        min_value=float(np.floor(dmin)),
        max_value=float(np.ceil(dmax)),
        value=(float(np.floor(dmin)), float(np.ceil(dmax))),
        step=0.1,
    )

# ---------------- Apply filters ---------------- #
filtered = filter_frame(
    df,
    cols,
    territory=territory,
    geo_archetype=geo_arch,
    courier_flow=courier_flow,
    merchant_surface=merchant_surface,
    date_range=date_range,
    pickup_range=pickup_range,
    dropoff_range=dropoff_range,
)

st.caption(f"Filtered rows: {filtered.shape[0]:,} / Total rows: {df.shape[0]:,}")

# ---------------- KPIs ---------------- #
st.title("ATD Dashboard")
atd_col = cols.get("atd")
kpis = kpi_series(filtered, atd_col)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Trips", f"{kpis['count']:,}")
c2.metric("ATD mean", f"{kpis['mean']:.2f}" if not np.isnan(kpis['mean']) else "—")
c3.metric("ATD median", f"{kpis['median']:.2f}" if not np.isnan(kpis['median']) else "—")
c4.metric("ATD P90", f"{kpis['p90']:.2f}" if not np.isnan(kpis['p90']) else "—")

getattr(st, "divider", lambda: st.markdown("---"))()

# ---------------- Charts ---------------- #
if atd_col:
    # 0) Daily lines: ATD + Trips (dual axis)
    if filtered["_eater_request_dt"].notna().any():
        daily = (
            filtered.assign(date=filtered["_eater_request_dt"].dt.date)
            .groupby("date")[atd_col]
            .agg(ATD_mean="mean", count="size")
            .reset_index()
        )
        st.subheader("Daily ATD and Trips")
        st.altair_chart(dual_axis_daily(daily), use_container_width=True)

    # ===== Business segmentations =====
    for dim_key, label in [
        ("territory", "Territory"),
        ("geo_archetype", "Geo archetype"),
        ("courier_flow", "Courier flow"),
        ("merchant_surface", "Merchant surface"),
    ]:
        if cols.get(dim_key):
            df_agg = agg_by(filtered, cols[dim_key], atd_col)
            st.subheader(f"Average ATD by {label}")
            st.altair_chart(
                bar_chart(df_agg, label, "ATD_mean", ATD_COLOR, label=True),
                use_container_width=True,
            )
            st.subheader(f"Trips by {label}")
            st.altair_chart(
                bar_chart(df_agg, label, "count", TRIPS_COLOR, label=True),
                use_container_width=True,
            )

    # ===== Temporal breakdown =====
    st.markdown("### Temporal breakdown")

    # Day of week (Mon→Sun)
    if "day_of_week" in filtered.columns:
        order_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        filtered["_dow_label"] = filtered["day_of_week"].map(day_map)
        df_dow = agg_by(filtered, "_dow_label", atd_col)

        st.subheader("Average ATD by day of week")
        st.altair_chart(
            bar_chart(df_dow, "day of week", "ATD_mean", ATD_COLOR, order_days, True),
            use_container_width=True,
        )
        st.subheader("Trips by day of week")
        st.altair_chart(
            bar_chart(df_dow, "day of week", "count", TRIPS_COLOR, order_days, True),
            use_container_width=True,
        )

    # Hour of day (0→23)
    if "hour_of_day" in filtered.columns:
        order_hours = list(range(24))
        df_hour = agg_by(filtered, "hour_of_day", atd_col)

        st.subheader("Average ATD by hour of day")
        st.altair_chart(
            bar_chart(df_hour, "hour of day", "ATD_mean", ATD_COLOR, order_hours, True),
            use_container_width=True,
        )
        st.subheader("Trips by hour of day")
        st.altair_chart(
            bar_chart(df_hour, "hour of day", "count", TRIPS_COLOR, order_hours, True),
            use_container_width=True,
        )

    # Weekend vs Weekday
    if "is_weekend" in filtered.columns:
        order_weekend = ["Weekday", "Weekend"]
        filtered["_is_weekend_label"] = np.where(filtered["is_weekend"], "Weekend", "Weekday")
        df_wknd = agg_by(filtered, "_is_weekend_label", atd_col)

        st.subheader("Average ATD by weekend vs weekday")
        st.altair_chart(
            bar_chart(df_wknd, "weekend vs weekday", "ATD_mean", ATD_COLOR, order_weekend, True),
            use_container_width=True,
        )
        st.subheader("Trips by weekend vs weekday")
        st.altair_chart(
            bar_chart(df_wknd, "weekend vs weekday", "count", TRIPS_COLOR, order_weekend, True),
            use_container_width=True,
        )

    # 3) Scatter: Pickup vs Dropoff (bubble size ~ ATD)
    if pickup_col and dropoff_col:
        st.subheader("ATD vs distances (Pickup vs Dropoff)")
        sample = filtered[[pickup_col, dropoff_col, atd_col]].dropna()
        if sample.shape[0] > 200_000:
            sample = sample.sample(200_000, random_state=7)

        scatter = (
            alt.Chart(sample)
            .mark_circle(opacity=0.4, color=ATD_COLOR)
            .encode(
                x=alt.X(f"{pickup_col}:Q", title="Pickup distance"),
                y=alt.Y(f"{dropoff_col}:Q", title="Dropoff distance"),
                size=alt.Size(f"{atd_col}:Q", title="ATD"),
                tooltip=[pickup_col, dropoff_col, atd_col],
            )
            .properties(height=360)
        )
        st.altair_chart(scatter, use_container_width=True)

    # 4) ATD distribution
    st.subheader("ATD distribution")
    hist = (
        alt.Chart(filtered[[atd_col]].dropna())
        .mark_area(opacity=0.6, color=ATD_COLOR)
        .encode(
            x=alt.X(f"{atd_col}:Q", bin=alt.Bin(maxbins=50), title="ATD"),
            y=alt.Y("count():Q", title="Trips (n)"),
            tooltip=[alt.Tooltip("count():Q", title="Trips (n)", format=",")],
        )
        .properties(height=300)
    )
    st.altair_chart(hist, use_container_width=True)

else:
    st.info("ATD column not found.")
