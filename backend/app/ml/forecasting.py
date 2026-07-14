"""
Forecasting layer.

Implements lightweight, dependency-friendly forecasting models (moving
average, linear/regression-based, and seasonal-naive) plus a simple
"auto" mode that backtests each candidate and picks the best performer.
This keeps the service runnable without heavyweight/optional deps
(Prophet, TensorFlow) while still satisfying the regression + seasonal
modeling requirements. Swapping in Prophet/ARIMA/LSTM later only means
implementing a new `BaseForecaster` and registering it below.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from app.services.preprocessing import add_time_features


@dataclass
class ForecastOutput:
    timestamps: List[pd.Timestamp]
    predicted: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    model_used: str
    mae: float
    mape: float


class BaseForecaster:
    name = "base"

    def fit_predict(self, series: pd.DataFrame, horizon_hours: int) -> Tuple[np.ndarray, np.ndarray]:
        """Returns (predictions, residual_std_per_step) — implemented by subclasses."""
        raise NotImplementedError


class MovingAverageForecaster(BaseForecaster):
    """Exponentially weighted moving average with hour-of-day seasonal adjustment."""
    name = "moving_average"

    def fit_predict(self, series: pd.DataFrame, horizon_hours: int) -> Tuple[np.ndarray, np.ndarray]:
        values = series["vehicle_count"]
        ewm_level = values.ewm(span=max(3, min(24, len(values) // 2))).mean().iloc[-1]

        hourly_profile = series.groupby(series.index.hour)["vehicle_count"].mean()
        overall_mean = values.mean() or 1.0
        seasonal_factor = (hourly_profile / overall_mean).to_dict()

        last_ts = series.index[-1]
        future_index = pd.date_range(last_ts + pd.Timedelta(hours=1), periods=horizon_hours, freq="h")

        preds = []
        for ts in future_index:
            factor = seasonal_factor.get(ts.hour, 1.0)
            preds.append(max(0.0, ewm_level * factor))

        resid_std = float(values.diff().dropna().std() or values.std() or 1.0)
        return np.array(preds), np.full(horizon_hours, resid_std)


class LinearRegressionForecaster(BaseForecaster):
    """Regression on engineered time features (hour, day-of-week, trend, weekend flag)."""
    name = "linear"

    def _build_features(self, index: pd.DatetimeIndex, t0) -> np.ndarray:
        hours = index.hour.values
        dows = index.dayofweek.values
        trend = np.array([(ts - t0).total_seconds() / 3600.0 for ts in index])
        is_weekend = (dows >= 5).astype(float)
        hour_sin = np.sin(2 * np.pi * hours / 24)
        hour_cos = np.cos(2 * np.pi * hours / 24)
        dow_sin = np.sin(2 * np.pi * dows / 7)
        dow_cos = np.cos(2 * np.pi * dows / 7)
        return np.column_stack([trend, hour_sin, hour_cos, dow_sin, dow_cos, is_weekend])

    def fit_predict(self, series: pd.DataFrame, horizon_hours: int) -> Tuple[np.ndarray, np.ndarray]:
        t0 = series.index[0]
        X = self._build_features(series.index, t0)
        y = series["vehicle_count"].values

        model = LinearRegression()
        model.fit(X, y)

        fitted = model.predict(X)
        residuals = y - fitted
        resid_std = float(residuals.std() or 1.0)

        last_ts = series.index[-1]
        future_index = pd.date_range(last_ts + pd.Timedelta(hours=1), periods=horizon_hours, freq="h")
        X_future = self._build_features(future_index, t0)
        preds = np.clip(model.predict(X_future), 0, None)

        return preds, np.full(horizon_hours, resid_std)


class SeasonalNaiveForecaster(BaseForecaster):
    """Predicts each future hour using the historical average for that (dow, hour) bucket."""
    name = "seasonal"

    def fit_predict(self, series: pd.DataFrame, horizon_hours: int) -> Tuple[np.ndarray, np.ndarray]:
        df = series.copy()
        df["hour"] = df.index.hour
        df["dow"] = df.index.dayofweek

        bucket_mean = df.groupby(["dow", "hour"])["vehicle_count"].mean()
        bucket_std = df.groupby(["dow", "hour"])["vehicle_count"].std().fillna(df["vehicle_count"].std() or 1.0)
        overall_mean = df["vehicle_count"].mean() or 1.0
        overall_std = df["vehicle_count"].std() or 1.0

        last_ts = series.index[-1]
        future_index = pd.date_range(last_ts + pd.Timedelta(hours=1), periods=horizon_hours, freq="h")

        preds, stds = [], []
        for ts in future_index:
            key = (ts.dayofweek, ts.hour)
            preds.append(bucket_mean.get(key, overall_mean))
            stds.append(bucket_std.get(key, overall_std))
        return np.array(preds), np.array(stds)


FORECASTER_REGISTRY = {
    "moving_average": MovingAverageForecaster,
    "linear": LinearRegressionForecaster,
    "seasonal": SeasonalNaiveForecaster,
}


def _backtest_mae(forecaster: BaseForecaster, series: pd.DataFrame, test_size: int) -> float:
    """Simple holdout backtest: fit on all-but-last `test_size` hours, score on the tail."""
    if len(series) <= test_size + MIN_TRAIN_ROWS:
        train = series
        test = None
    else:
        train = series.iloc[:-test_size]
        test = series.iloc[-test_size:]

    if test is None or test.empty:
        return float("inf")

    preds, _ = forecaster.fit_predict(train, len(test))
    actual = test["vehicle_count"].values
    return float(np.mean(np.abs(preds - actual)))


MIN_TRAIN_ROWS = 6


def select_best_model(series: pd.DataFrame, model_type: str = "auto") -> BaseForecaster:
    if model_type != "auto":
        cls = FORECASTER_REGISTRY.get(model_type, LinearRegressionForecaster)
        return cls()

    test_size = min(12, max(3, len(series) // 5))
    scores = {}
    for key, cls in FORECASTER_REGISTRY.items():
        try:
            scores[key] = _backtest_mae(cls(), series, test_size)
        except Exception:
            scores[key] = float("inf")

    best_key = min(scores, key=scores.get)
    if scores[best_key] == float("inf"):
        best_key = "seasonal"
    return FORECASTER_REGISTRY[best_key]()


def generate_forecast(series: pd.DataFrame, horizon_hours: int, model_type: str = "auto") -> ForecastOutput:
    """
    Main entry point: fits the chosen (or auto-selected) model on the full
    series and produces a horizon-hour forecast with confidence bounds,
    plus an honest accuracy estimate via holdout backtesting.
    """
    forecaster = select_best_model(series, model_type)

    # Accuracy: backtest on the most recent slice actually held out from training
    test_size = min(12, max(3, len(series) // 5))
    mae = _backtest_mae(forecaster.__class__(), series, test_size)
    mape = None

    if len(series) > test_size + MIN_TRAIN_ROWS:
        train = series.iloc[:-test_size]
        test = series.iloc[-test_size:]
        preds_bt, _ = forecaster.__class__().fit_predict(train, len(test))
        actual = test["vehicle_count"].values
        nonzero = np.where(actual == 0, 1e-6, actual)
        mape = float(np.mean(np.abs((actual - preds_bt) / nonzero)) * 100)

    preds, resid_std = forecaster.fit_predict(series, horizon_hours)
    last_ts = series.index[-1]
    future_index = pd.date_range(last_ts + pd.Timedelta(hours=1), periods=horizon_hours, freq="h")

    z = 1.645  # ~90% interval
    lower = np.clip(preds - z * resid_std, 0, None)
    upper = preds + z * resid_std

    return ForecastOutput(
        timestamps=list(future_index),
        predicted=preds,
        lower=lower,
        upper=upper,
        model_used=forecaster.name,
        mae=round(mae, 2) if mae != float("inf") else 0.0,
        mape=round(mape, 2) if mape is not None else 0.0,
    )


def volume_to_congestion(volume: np.ndarray, historical_max: float) -> np.ndarray:
    """Normalize predicted volume into a 0-1 congestion index relative to observed capacity."""
    cap = historical_max if historical_max and historical_max > 0 else (volume.max() or 1.0)
    return np.clip(volume / cap, 0, 1.5)  # allow >1 to signal over-capacity


def compute_peak_hours(series: pd.DataFrame, top_n: int = 5) -> List[dict]:
    """Aggregate historical + recent data to identify recurring peak-traffic hours."""
    df = series.copy()
    df["hour"] = df.index.hour
    profile = df.groupby("hour")["vehicle_count"].agg(["mean", "std"]).fillna(0)
    profile = profile.sort_values("mean", ascending=False).head(top_n)

    results = []
    for hour, row in profile.iterrows():
        results.append({
            "hour": int(hour),
            "label": f"{hour:02d}:00 - {(hour + 1) % 24:02d}:00",
            "avg_volume": round(float(row["mean"]), 2),
            "volatility": round(float(row["std"]), 2),
        })
    return results
