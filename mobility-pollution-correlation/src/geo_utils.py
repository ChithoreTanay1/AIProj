"""Geospatial helpers: distance calc and transit-exposure aggregation."""
import math

import pandas as pd

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def compute_transit_exposure(
    stations_df: pd.DataFrame, stops_df: pd.DataFrame, radius_km: float
) -> pd.DataFrame:
    """For each monitoring station, count DKV stops within radius_km and,
    if a 'trips_per_day' column is present on stops_df, sum scheduled trips
    within that radius too.

    Returns one row per station_id: stop_count, trips_per_day (if available).
    If stops_df is empty, returns zeros for every station (monitoring-only mode).
    """
    rows = []
    has_trips = "trips_per_day" in stops_df.columns if not stops_df.empty else False

    for _, station in stations_df.iterrows():
        if stops_df.empty:
            rows.append({"station_id": station["station_id"], "stop_count": 0, "trips_per_day": 0.0})
            continue

        dists = stops_df.apply(
            lambda s: haversine_km(station["lat"], station["lon"], s["stop_lat"], s["stop_lon"]),
            axis=1,
        )
        nearby = stops_df[dists <= radius_km]
        row = {"station_id": station["station_id"], "stop_count": len(nearby)}
        row["trips_per_day"] = nearby["trips_per_day"].sum() if has_trips else float("nan")
        rows.append(row)

    return pd.DataFrame(rows)
