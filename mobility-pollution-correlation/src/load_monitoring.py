"""Load the KER sensor network data (air quality + noise) from the
monitoring_2026-05-21_2026-06-19 export folder.

Each DEB-KER## folder contains one or more xlsx files named
DEB-KER##_Levego.xlsx (air), DEB-KER##_Zaj.xlsx (noise), and
DEB-KER##_Felszin_alatti_viz.xlsx (groundwater, not used here).

All three share the same tidy long format:
    timestamp    | Location                              | Merőeszköz | érték | mértékegység
    2026-05-21-02-00 | Name (lat, lon)                    | PM2.5      | 6.6   | µg/m3
"""
import glob
import os
import re

import pandas as pd

LOCATION_RE = re.compile(r"\(([-\d.]+),\s*([-\d.]+)\)")


def _parse_location(location: str):
    """Extract (name, lat, lon) from a 'Name (lat, lon)' string."""
    match = LOCATION_RE.search(location)
    if not match:
        return location.strip(), None, None
    lat, lon = float(match.group(1)), float(match.group(2))
    name = location[: match.start()].strip().rstrip(",").strip()
    return name, lat, lon


def _station_id_from_folder(folder_path: str) -> str:
    return os.path.basename(folder_path.rstrip("/\\"))


def load_station_metadata(monitoring_dir: str) -> pd.DataFrame:
    """One row per DEB-KER station: station_id, name, lat, lon."""
    rows = []
    for folder in sorted(glob.glob(os.path.join(monitoring_dir, "DEB-KER*"))):
        station_id = _station_id_from_folder(folder)
        any_file = sorted(glob.glob(os.path.join(folder, "*.xlsx")))
        if not any_file:
            continue
        df = pd.read_excel(any_file[0], nrows=1)
        if df.empty:
            continue
        name, lat, lon = _parse_location(df["Location"].iloc[0])
        rows.append({"station_id": station_id, "name": name, "lat": lat, "lon": lon})
    return pd.DataFrame(rows)


def _load_measure(monitoring_dir: str, suffix: str) -> pd.DataFrame:
    """Load and concatenate every DEB-KER##_<suffix>.xlsx file found."""
    frames = []
    for folder in sorted(glob.glob(os.path.join(monitoring_dir, "DEB-KER*"))):
        station_id = _station_id_from_folder(folder)
        path = os.path.join(folder, f"{station_id}_{suffix}.xlsx")
        if not os.path.exists(path):
            continue
        df = pd.read_excel(path)
        df = df.rename(
            columns={
                "Mérőeszköz": "metric",
                "érték": "value",
                "mértékegység": "unit",
                "timestamp": "timestamp",
                "Location": "location",
            }
        )
        df["station_id"] = station_id
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d-%H-%M")
        frames.append(df[["station_id", "timestamp", "metric", "value", "unit"]])
    if not frames:
        return pd.DataFrame(columns=["station_id", "timestamp", "metric", "value", "unit"])
    return pd.concat(frames, ignore_index=True)


def load_air_quality(monitoring_dir: str) -> pd.DataFrame:
    """Tidy long-format air quality readings for all stations."""
    return _load_measure(monitoring_dir, "Levego")


def load_noise(monitoring_dir: str) -> pd.DataFrame:
    """Tidy long-format noise readings for all stations."""
    return _load_measure(monitoring_dir, "Zaj")


def station_pollutant_summary(air_df: pd.DataFrame, noise_df: pd.DataFrame) -> pd.DataFrame:
    """One row per station with mean value for each pollutant/noise metric.

    Column names are the raw metric names (PM2.5, NO2, LAEQ nappali, ...).
    """
    air_wide = (
        air_df.groupby(["station_id", "metric"])["value"]
        .mean()
        .unstack("metric")
        if not air_df.empty
        else pd.DataFrame()
    )
    noise_wide = (
        noise_df.groupby(["station_id", "metric"])["value"]
        .mean()
        .unstack("metric")
        if not noise_df.empty
        else pd.DataFrame()
    )
    summary = air_wide.join(noise_wide, how="outer")
    summary.index.name = "station_id"
    return summary.reset_index()
