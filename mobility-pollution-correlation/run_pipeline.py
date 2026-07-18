"""Mobility <-> Pollution Correlation pipeline — DEIK.AI Challenge 2026.

Loads the KER sensor network (air quality + noise) and DKV transit data,
computes transit exposure per monitoring station, correlates it against
pollution/noise readings, and writes charts + a summary CSV + an interactive
map to outputs/.

Run: python run_pipeline.py   (see instructions.md for setup)
"""
import os

import pandas as pd
import yaml

from src.correlate import compute_correlations, fit_simple_regression, merge_station_transit
from src.geo_utils import compute_transit_exposure
from src.load_dkv import is_dkv_data_available, load_dkv_stops
from src.load_monitoring import (
    load_air_quality,
    load_noise,
    load_station_metadata,
    station_pollutant_summary,
)
from src.visualize import build_station_map, plot_pollutant_by_station, plot_transit_vs_pollutant

HERE = os.path.dirname(os.path.abspath(__file__))


def load_config(path: str = "config.yaml") -> dict:
    with open(os.path.join(HERE, path), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(HERE, path)


def main():
    cfg = load_config()
    monitoring_dir = resolve(cfg["monitoring_dir"])
    dkv_dir = resolve(cfg["dkv_dir"])
    outputs_dir = resolve(cfg["outputs_dir"])
    radius_km = cfg["radius_km"]
    pollutants = cfg["pollutants"]
    noise_metrics = cfg["noise_metrics"]
    transit_metrics = cfg["transit_metrics"]

    os.makedirs(outputs_dir, exist_ok=True)

    print("=" * 70)
    print("STEP 1/5: Loading KER monitoring station metadata + readings")
    print("=" * 70)
    stations = load_station_metadata(monitoring_dir)
    air = load_air_quality(monitoring_dir)
    noise = load_noise(monitoring_dir)
    print(f"  {len(stations)} stations, {len(air)} air readings, {len(noise)} noise readings")
    pollutant_summary = station_pollutant_summary(air, noise)

    print()
    print("=" * 70)
    print("STEP 2/5: Loading DKV transport data")
    print("=" * 70)
    dkv_available = is_dkv_data_available(dkv_dir)
    stops = load_dkv_stops(dkv_dir)
    print(f"  DKV data available: {dkv_available}  ({len(stops)} stops loaded)")

    print()
    print("=" * 70)
    print(f"STEP 3/5: Computing transit exposure (radius = {radius_km} km)")
    print("=" * 70)
    transit_exposure = compute_transit_exposure(stations, stops, radius_km)

    print()
    print("=" * 70)
    print("STEP 4/5: Correlating transit exposure with pollution/noise")
    print("=" * 70)
    merged = merge_station_transit(pollutant_summary, transit_exposure, stations)
    merged.to_csv(os.path.join(outputs_dir, "station_summary.csv"), index=False)
    print(f"  Wrote outputs/station_summary.csv ({len(merged)} stations)")

    target_metrics = [m for m in (pollutants + noise_metrics) if m in merged.columns]
    corr = compute_correlations(merged, target_metrics, transit_metrics)
    corr.to_csv(os.path.join(outputs_dir, "correlations.csv"), index=False)
    print(f"  Wrote outputs/correlations.csv ({len(corr)} metric pairs)")

    if not dkv_available:
        print(
            "  NOTE: no DKV data yet, so all correlations above are NaN "
            "(transit exposure is constant/zero for every station). "
            "This is expected in monitoring-only mode."
        )

    regressions = []
    for t_col in transit_metrics:
        for p_col in target_metrics:
            reg = fit_simple_regression(merged, target=p_col, feature=t_col)
            if reg:
                regressions.append(reg)
    if regressions:
        pd.DataFrame(regressions).to_csv(os.path.join(outputs_dir, "regressions.csv"), index=False)
        print(f"  Wrote outputs/regressions.csv ({len(regressions)} fitted models)")

    print()
    print("=" * 70)
    print("STEP 5/5: Generating charts and map")
    print("=" * 70)
    made = []
    for p in target_metrics:
        path = plot_pollutant_by_station(merged, p, outputs_dir)
        if path:
            made.append(path)
    for t_col in transit_metrics:
        for p_col in target_metrics:
            path = plot_transit_vs_pollutant(merged, t_col, p_col, outputs_dir)
            if path:
                made.append(path)
    map_color_metric = "PM2.5" if "PM2.5" in merged.columns else (target_metrics[0] if target_metrics else None)
    if map_color_metric:
        map_path = build_station_map(merged, stops, outputs_dir, color_by=map_color_metric)
        if map_path:
            made.append(map_path)
    print(f"  Wrote {len(made)} files to {outputs_dir}")

    print()
    print("Done. See outputs/station_summary.csv, outputs/correlations.csv, and the charts/map.")


if __name__ == "__main__":
    main()
