"""
Utility helpers for the ATD Streamlit dashboard.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import altair as alt
from typing import Iterable, Optional, Tuple

# ===== Config colores =====
ATD_COLOR = "#03c167"
TRIPS_COLOR = "#ffc043"

# ===== Column mapping =====
CANONICAL_COLS = {
    "territory": ["territory", "Territory"],
    "geo_archetype": ["geo_archetype", "Geo Archetype", "Geo_Archetype"],
    "courier_flow": ["courier_flow", "Courier flow", "delivery_flow", "workflow"],
    "merchant_surface": ["merchant_surface", "Merchant surface", "merchantSurface"],
    "eater_request_ts": [
        "eater_request_timestamp_local",
        "eater_request_ts_local",
        "eater_request_time",
        "eater_request",
    ],
    "pickup_distance": ["pickup_distance", "pickup_km"],
    "dropoff_distance": ["dropoff_distance", "dropoff_km"],
    "atd": ["ATD", "atd", "avg_time_to_deliver"],
}

def find_first_present(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None

def resolve_columns(df: pd.DataFrame) -> dict:
    mapping = {}
    for key, candidates in CANONICAL_COLS.items():
        mapping[key] = find_first_present(df, candidates)
    return mapping

def _parse_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)

def add_derived_fields(df: pd.DataFrame, cols: dict) -> pd.DataFrame:
    out = df.copy()
    eat_col = cols.get("eater_request_ts")
    if eat_col and eat_col in out.columns:
        out["_eater_request_dt"] = _parse_datetime(out[eat_col])
    else:
        out["_eater_request_dt"] = pd.NaT
    for nm in ("pickup_distance", "dropoff_distance", "atd"):
        col = cols.get(nm)
        if col and col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out

def filter_frame(
    df: pd.DataFrame,
    cols: dict,
    territory=None,
    geo_archetype=None,
    courier_flow=None,
    merchant_surface=None,
    date_range=None,
    pickup_range=None,
    dropoff_range=None,
):
    mask = pd.Series(True, index=df.index)
    def apply_cat(col_key, values):
        nonlocal mask
        col = cols.get(col_key)
        if col and values:
            mask &= df[col].isin(values)
    apply_cat("territory", territory)
    apply_cat("geo_archetype", geo_archetype)
    apply_cat("courier_flow", courier_flow)
    apply_cat("merchant_surface", merchant_surface)
    if date_range and cols.get("eater_request_ts"):
        start, end = date_range
        dt = df["_eater_request_dt"]
        mask &= (dt >= start) & (dt <= end)
    if pickup_range and cols.get("pickup_distance"):
        mask &= df[cols["pickup_distance"]].between(*pickup_range)
    if dropoff_range and cols.get("dropoff_distance"):
        mask &= df[cols["dropoff_distance"]].between(*dropoff_range)
    return df[mask]

def kpi_series(df: pd.DataFrame, atd_col: Optional[str]) -> dict:
    if not atd_col or atd_col not in df.columns or df[atd_col].dropna().empty:
        return {"count": 0, "mean": np.nan, "median": np.nan, "p90": np.nan}
    s = df[atd_col].dropna().astype(float)
    return {"count": int(s.count()), "mean": s.mean(), "median": s.median(), "p90": s.quantile(0.9)}

# ===== Gráficas =====
def agg_by(df_in, dim, atd_col):
    return (
        df_in.groupby(dim)[atd_col]
        .agg(ATD_mean="mean", count="size")
        .reset_index()
        .rename(columns={dim: "dim"})
    )

def bar_chart(df_in, x_title, y_field, color, domain_order=None, label=False):
    data = df_in.copy()
    x_args = {"field": "dim", "type": "nominal", "title": x_title}
    if domain_order is not None:
        x_args["scale"] = alt.Scale(domain=domain_order)
    bars = (
        alt.Chart(data)
        .mark_bar(color=color)
        .encode(
            x=alt.X(**x_args),
            y=alt.Y(f"{y_field}:Q", title=y_field),
            tooltip=[alt.Tooltip("dim:N", title=x_title), alt.Tooltip(f"{y_field}:Q", title=y_field, format=".2f")],
        )
        .properties(height=320)
    )
    if label:
        txt = (
            alt.Chart(data)
            .mark_text(dy=-6, color="white")
            .encode(
                x=alt.X(**x_args),
                y=alt.Y(f"{y_field}:Q"),
                text=alt.Text(f"{y_field}:Q", format=".2f" if y_field == "ATD_mean" else ","),
            )
        )
        return bars + txt
    return bars

def dual_axis_daily(daily_df):
    base = alt.Chart(daily_df).encode(x=alt.X("date:T", title="Date"))
    atd_line = base.mark_line(color=ATD_COLOR).encode(
        y=alt.Y("ATD_mean:Q", axis=alt.Axis(title="ATD (mean)")),
        tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("ATD_mean:Q", title="ATD mean", format=".2f")],
    )
    trips_line = base.mark_line(color=TRIPS_COLOR).encode(
        y=alt.Y("count:Q", axis=alt.Axis(title="Trips", orient="right")),
        tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("count:Q", title="Trips (n)", format=",")],
    )
    return alt.layer(atd_line, trips_line).resolve_scale(y="independent").properties(height=360)
