"""Merge pollution/noise summaries with transit exposure and quantify the
relationship between them.
"""
import numpy as np
import pandas as pd
from scipy import stats


def merge_station_transit(
    pollutant_summary: pd.DataFrame,
    transit_exposure: pd.DataFrame,
    stations_meta: pd.DataFrame,
) -> pd.DataFrame:
    """One row per station: name, lat, lon, transit exposure, pollutant means."""
    merged = stations_meta.merge(transit_exposure, on="station_id", how="left")
    merged = merged.merge(pollutant_summary, on="station_id", how="left")
    return merged


def compute_correlations(
    merged: pd.DataFrame, pollutant_cols: list, transit_cols: list
) -> pd.DataFrame:
    """Pearson r and p-value between each transit metric and each pollutant.

    Returns a tidy DataFrame: transit_metric, pollutant, r, p_value, n.
    NaNs (e.g. all-zero transit exposure in monitoring-only mode) are dropped
    pairwise; if fewer than 3 valid points remain, r/p are reported as NaN.
    """
    rows = []
    for t_col in transit_cols:
        if t_col not in merged.columns:
            continue
        for p_col in pollutant_cols:
            if p_col not in merged.columns:
                continue
            pair = merged[[t_col, p_col]].dropna()
            if len(pair) < 3 or pair[t_col].nunique() < 2:
                rows.append(
                    {"transit_metric": t_col, "pollutant": p_col, "r": np.nan, "p_value": np.nan, "n": len(pair)}
                )
                continue
            r, p = stats.pearsonr(pair[t_col], pair[p_col])
            rows.append({"transit_metric": t_col, "pollutant": p_col, "r": r, "p_value": p, "n": len(pair)})
    return pd.DataFrame(rows)


def fit_simple_regression(merged: pd.DataFrame, target: str, feature: str) -> dict:
    """Single-predictor OLS: target ~ feature. Returns slope, intercept, r2, p_value.

    Returns None if there isn't enough valid, varying data to fit.
    """
    pair = merged[[feature, target]].dropna()
    if len(pair) < 3 or pair[feature].nunique() < 2:
        return None
    result = stats.linregress(pair[feature], pair[target])
    return {
        "feature": feature,
        "target": target,
        "slope": result.slope,
        "intercept": result.intercept,
        "r2": result.rvalue ** 2,
        "p_value": result.pvalue,
        "n": len(pair),
    }
