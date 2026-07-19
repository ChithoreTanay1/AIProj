"""Load DKV Debrecen Transport Ltd. data.

The real export lives in data/dkv/. Main file is "List of bus stops.xlsx" —
687 platforms, coordinates packed into one "Coordinates" column as
"lon, lat". We join that against the monthly "Summary stop statistics"
exports to get a rough passenger-frequency number per stop name, which is
what we use as a trips_per_day stand-in since there's no real published
schedule/frequency file. "Service Schedule.xlsx" also exists but isn't
parsed yet.

Kept two older guesses at the schema around as fallbacks, in case DKV ever
ships something else:

- GTFS style (stops.txt, optionally routes/trips/stop_times.txt) — the
  format most transit agencies actually export.
- a generic CSV/XLSX with lat/lon-ish column names.

If nothing matches any of these, load_dkv_stops just hands back an empty
frame and the rest of the pipeline keeps running in monitoring-only mode
instead of crashing.
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
    """DKV packs coordinates as a single "lon, lat" string — split that
    into two numeric columns."""
    parts = series.astype(str).str.split(",", n=1, expand=True)
    lon = pd.to_numeric(parts[0], errors="coerce")
    lat = pd.to_numeric(parts[1], errors="coerce") if parts.shape[1] > 1 else pd.Series(
        float("nan"), index=series.index
    )
    return lat, lon


def _load_stop_passenger_frequency(dkv_dir: str) -> pd.Series:
    """Average monthly passenger frequency (boardings + alightings) per
    stop name, from the Summary stop statistics exports — our stand-in
    for trips_per_day.

    These sheets have a messy multi-row header, so the real data only
    starts at row 9. Column 1 ends up being the stop name, column 8 the
    total passenger frequency, once read with skiprows=8.
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
    """Parse the real "List of bus stops.xlsx" export — one row per
    platform, coordinates packed into a single "lon, lat" column."""
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
