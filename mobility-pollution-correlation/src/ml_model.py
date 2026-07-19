"""Multivariate ML: predict pollutant levels from transit exposure + weather
together, instead of the one-metric-at-a-time correlations in correlate.py.

With only ~16 stations, a single train/test split is meaningless (test set
of 2-3 points, huge variance) — so every model is scored with leave-one-out
cross-validation (fit on 15, predict the 1 held out, repeat for each
station) to get an honest, if noisy, out-of-sample estimate. Each model is
also compared against a trivial "always predict the mean" baseline, since
with this little data a Random Forest can easily do *worse* than the
baseline — that comparison is the real signal of whether the model learned
anything, not the R2 alone.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneOut

FEATURE_COLS = ["stop_count", "trips_per_day", "Humidity", "Pressure", "Wind_Speed", "Wind_Direction"]


def _loocv_predict(X: np.ndarray, y: np.ndarray, **rf_kwargs) -> np.ndarray:
    loo = LeaveOneOut()
    preds = np.full(len(y), np.nan)
    for train_idx, test_idx in loo.split(X):
        model = RandomForestRegressor(random_state=42, **rf_kwargs)
        model.fit(X[train_idx], y[train_idx])
        preds[test_idx] = model.predict(X[test_idx])
    return preds


def train_pollutant_models(
    merged: pd.DataFrame, pollutants: list, feature_cols: list = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit one small Random Forest per pollutant on transit+weather features.

    Returns (performance_df, importance_df):
      performance_df: pollutant, n, loocv_r2, loocv_rmse,
                       baseline_rmse_mean_predictor, beats_mean_baseline
      importance_df:  pollutant, feature, importance (from a model refit on
                       all stations, for interpretability only — not the
                       same model used for the LOOCV scores)

    Skips a pollutant if fewer than 6 stations have complete feature+target
    data (not enough for LOOCV to mean anything).
    """
    feature_cols = feature_cols or FEATURE_COLS
    rf_kwargs = dict(n_estimators=200, max_depth=3)

    perf_rows = []
    importance_rows = []

    for pollutant in pollutants:
        cols = feature_cols + [pollutant]
        data = merged[cols].dropna()
        if len(data) < 6:
            continue
        X = data[feature_cols].to_numpy()
        y = data[pollutant].to_numpy()

        preds = _loocv_predict(X, y, **rf_kwargs)
        r2 = r2_score(y, preds)
        rmse = float(np.sqrt(mean_squared_error(y, preds)))
        baseline_rmse = float(np.sqrt(mean_squared_error(y, np.full_like(y, y.mean()))))

        perf_rows.append(
            {
                "pollutant": pollutant,
                "n": len(data),
                "loocv_r2": r2,
                "loocv_rmse": rmse,
                "baseline_rmse_mean_predictor": baseline_rmse,
                "beats_mean_baseline": rmse < baseline_rmse,
            }
        )

        full_model = RandomForestRegressor(random_state=42, **rf_kwargs)
        full_model.fit(X, y)
        for feat, imp in zip(feature_cols, full_model.feature_importances_):
            importance_rows.append({"pollutant": pollutant, "feature": feat, "importance": imp})

    return pd.DataFrame(perf_rows), pd.DataFrame(importance_rows)
