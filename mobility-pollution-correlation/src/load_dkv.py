"""Load DKV Debrecen Transport Ltd. data.

The real DKV export (DEIK.AI Challenge 2026) lives in data/dkv/:
    "List of bus stops.xlsx"           one row per platform, with a combined
                                        "Coordinates" column ("lon, lat")
    "Summary stop statistics/<year>/<month>.xlsx"
                                        monthly per-stop boarding/alighting
                                        counts, keyed by stop name (multi-row
                                        header, data starts at row 9)
    "Service Schedule.xlsx"            route/trip level departure schedule
                                        (not currently parsed — see below)

`_load_bus_stops_export` reads the stop list for geometry and joins in an
average passenger-frequency figure (as a trips_per_day proxy) from the
Summary stop statistics files, matched on stop name.

Two older *assumed* schemas are kept as fallbacks for portability (e.g. if
DKV ever ships a GTFS export instead), and the loader still degrades
gracefully to an empty result (monitoring-only mode) if nothing recognizable
is found:

Fallback schema 1 — GTFS-style (standard for public transit agencies):
    data/dkv/stops.txt       stop_id, stop_name, stop_lat, stop_lon
    data/dkv/routes.txt      route_id, route_short_name, route_long_name
    data/dkv/trips.txt       trip_id, route_id
    data/dkv/stop_times.txt  trip_id, stop_id, arrival_time
    (stop_times + trips together let us compute scheduled trips/day per stop)

Fallback schema 2 — generic flat export (CSV or XLSX):
    a single file with columns whose names contain "lat"/"lon" (or "lng")
    for stop coordinates, and optionally a trip-count-like column.
"""
import glob
import os

import pandas as pd

GTFS_REQUIRED = ["stops.txt"]
BUS_STOPS_FILE = "List of bus stops.xlsx"


def is_dkv_data_available(dkv_dir: str) -> bool:
    if not os.path.isdir(dkv_dir):
        return False
    has_real_export = os.path.exists(os.path.join(dkv_dir, BUS_STOPS_FILE))
    has_gtfs = all(os.path.exists(os.path.join(dkv_dir, f)) for f in GTFS_REQUIRED)
    has_generic = bool(glob.glob(os.path.join(dkv_dir, "*.csv"))) or bool(
        glob.glob(os.path.join(dkv_dir, "*.xlsx"))
    )
    return has_real_export or has_gtfs or has_generic


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


def _parse_coordinates(series: pd.Series):
    """Split a "lon, lat" string column (DKV's "Coordinates" format) into
    separate numeric lat/lon series."""
    parts = series.astype(str).str.split(",", n=1, expand=True)
    lon = pd.to_numeric(parts[0], errors="coerce")
    lat = pd.to_numeric(parts[1], errors="coerce") if parts.shape[1] > 1 else pd.Series(
        float("nan"), index=series.index
    )
    return lat, lon


def _load_stop_passenger_frequency(dkv_dir: str) -> pd.Series:
    """Average monthly passenger frequency (boardings + alightings) per stop
    name, from "Summary stop statistics/<year>/<month>.xlsx" exports. Used
    as a trips_per_day-like transit-exposure signal.

    Each file has a multi-row header (data starts at row index 8) with
    columns: Ident., Name, Planned stopping (APC, All), IN (Σ, Ø),
    OUT (Σ, Ø), Frequency of passengers (Σ, Ø), Occupancy..., Delay.
    Column 1 is Name, column 8 is Frequency of passengers Σ.
    """
    pattern = os.path.join(dkv_dir, "Summary stop statistics", "*", "*.xlsx")
    frames = []
    for path in glob.glob(pattern):
        try:
            raw = pd.read_excel(path, header=None, skiprows=8)
        except Exception:
            continue
        if raw.shape[1] < 9:
            continue
        sub = raw[[1, 8]].copy()
        sub.columns = ["stop_name", "passenger_freq"]
        sub["stop_name"] = sub["stop_name"].astype(str).str.strip()
        sub["passenger_freq"] = pd.to_numeric(sub["passenger_freq"], errors="coerce")
        frames.append(sub.dropna())
    if not frames:
        return pd.Series(dtype=float)
    all_freq = pd.concat(frames, ignore_index=True)
    return all_freq.groupby("stop_name")["passenger_freq"].mean()


def _load_bus_stops_export(dkv_dir: str) -> pd.DataFrame:
    """Parse DKV's real "List of bus stops.xlsx" export: one row per
    platform, with a combined "Coordinates" column ("lon, lat")."""
    df = pd.read_excel(os.path.join(dkv_dir, BUS_STOPS_FILE))
    lat, lon = _parse_coordinates(df["Coordinates"])
    out = pd.DataFrame(
        {
            "stop_id": df.index.astype(str),
            "stop_name": df["Bus stop"].astype(str).str.strip(),
            "stop_lat": lat,
            "stop_lon": lon,
        }
    ).dropna(subset=["stop_lat", "stop_lon"])

    freq = _load_stop_passenger_frequency(dkv_dir)
    if not freq.empty:
        # monthly total -> rough daily figure
        out["trips_per_day"] = (out["stop_name"].map(freq) / 30.0).fillna(0.0)

    return out.drop(columns="stop_name")


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

    if os.path.exists(os.path.join(dkv_dir, BUS_STOPS_FILE)):
        return _load_bus_stops_export(dkv_dir)
    if all(os.path.exists(os.path.join(dkv_dir, f)) for f in GTFS_REQUIRED):
        return _load_gtfs_style(dkv_dir)
    return _load_generic_table(dkv_dir)
