"""Load DKV Debrecen Transport Ltd. data.

IMPORTANT: as of writing, the actual DKV dataset file has not been supplied
(only its existence was mentioned in the challenge brief, exclusively for
DEIK.AI Challenge 2026 participants — no public URL). This loader is written
against two *assumed* schemas and degrades gracefully to an empty result
(monitoring-only mode) if neither is found, so the rest of the pipeline
always runs.

Once you have the real DKV export, drop it into data/dkv/ and re-run. If its
columns don't match either assumed schema below, adjust the parsing in
`_load_gtfs_style` or `_load_generic_table` accordingly.

Assumed schema 1 — GTFS-style (standard for public transit agencies):
    data/dkv/stops.txt       stop_id, stop_name, stop_lat, stop_lon
    data/dkv/routes.txt      route_id, route_short_name, route_long_name
    data/dkv/trips.txt       trip_id, route_id
    data/dkv/stop_times.txt  trip_id, stop_id, arrival_time
    (stop_times + trips together let us compute scheduled trips/day per stop)

Assumed schema 2 — generic flat export (CSV or XLSX):
    a single file with columns whose names contain "lat"/"lon" (or "lng")
    for stop coordinates, and optionally a trip-count-like column.
"""
import glob
import os

import pandas as pd

GTFS_REQUIRED = ["stops.txt"]


def is_dkv_data_available(dkv_dir: str) -> bool:
    if not os.path.isdir(dkv_dir):
        return False
    has_gtfs = all(os.path.exists(os.path.join(dkv_dir, f)) for f in GTFS_REQUIRED)
    has_generic = bool(glob.glob(os.path.join(dkv_dir, "*.csv"))) or bool(
        glob.glob(os.path.join(dkv_dir, "*.xlsx"))
    )
    return has_gtfs or has_generic


def _load_gtfs_style(dkv_dir: str) -> pd.DataFrame:
    stops = pd.read_csv(os.path.join(dkv_dir, "stops.txt"))
    stops = stops.rename(
        columns={c: c.strip().lower() for c in stops.columns}
    )
    keep = stops[["stop_id", "stop_lat", "stop_lon"]].copy()

    stop_times_path = os.path.join(dkv_dir, "stop_times.txt")
    trips_path = os.path.join(dkv_dir, "trips.txt")
    if os.path.exists(stop_times_path) and os.path.exists(trips_path):
        stop_times = pd.read_csv(stop_times_path)
        stop_times = stop_times.rename(columns={c: c.strip().lower() for c in stop_times.columns})
        trips_per_day = stop_times.groupby("stop_id")["trip_id"].nunique().rename("trips_per_day")
        keep = keep.merge(trips_per_day, on="stop_id", how="left")
        keep["trips_per_day"] = keep["trips_per_day"].fillna(0)

    return keep


def _find_column(columns, *keywords):
    lower = {c: c.lower() for c in columns}
    for col, low in lower.items():
        if any(k in low for k in keywords):
            return col
    return None


def _load_generic_table(dkv_dir: str) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(dkv_dir, "*.csv"))) + sorted(
        glob.glob(os.path.join(dkv_dir, "*.xlsx"))
    )
    frames = []
    for path in files:
        df = pd.read_csv(path) if path.endswith(".csv") else pd.read_excel(path)
        lat_col = _find_column(df.columns, "lat")
        lon_col = _find_column(df.columns, "lon", "lng")
        if lat_col is None or lon_col is None:
            continue  # not a stop/location table, skip
        trip_col = _find_column(df.columns, "trip", "frequency", "count")

        out = pd.DataFrame(
            {
                "stop_id": df.get("stop_id", pd.RangeIndex(len(df)).astype(str)),
                "stop_lat": pd.to_numeric(df[lat_col], errors="coerce"),
                "stop_lon": pd.to_numeric(df[lon_col], errors="coerce"),
            }
        )
        if trip_col is not None:
            out["trips_per_day"] = pd.to_numeric(df[trip_col], errors="coerce").fillna(0)
        frames.append(out.dropna(subset=["stop_lat", "stop_lon"]))

    if not frames:
        return pd.DataFrame(columns=["stop_id", "stop_lat", "stop_lon"])
    return pd.concat(frames, ignore_index=True)


def load_dkv_stops(dkv_dir: str) -> pd.DataFrame:
    """Returns a DataFrame with stop_id, stop_lat, stop_lon, and
    (if derivable) trips_per_day. Empty DataFrame if no DKV data is present.
    """
    if not is_dkv_data_available(dkv_dir):
        print(
            f"[load_dkv] No DKV data found in '{dkv_dir}'. "
            "Running in monitoring-only mode — transit exposure will be zero "
            "for all stations. Drop the real DKV export there to enable "
            "the mobility <-> pollution correlation."
        )
        return pd.DataFrame(columns=["stop_id", "stop_lat", "stop_lon"])

    if all(os.path.exists(os.path.join(dkv_dir, f)) for f in GTFS_REQUIRED):
        return _load_gtfs_style(dkv_dir)
    return _load_generic_table(dkv_dir)
