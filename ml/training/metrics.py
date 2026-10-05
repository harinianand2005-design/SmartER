"""Stable metric helpers shared by forecasting and resource models."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def regression_metrics(actual, predicted) -> dict[str, float]:
    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    non_zero = actual_array != 0
    mape = float(np.mean(np.abs((actual_array[non_zero] - predicted_array[non_zero]) / actual_array[non_zero])) * 100) if non_zero.any() else None
    values = {"mae": float(mean_absolute_error(actual_array, predicted_array)), "rmse": float(np.sqrt(mean_squared_error(actual_array, predicted_array))), "r2": float(r2_score(actual_array, predicted_array))}
    if mape is not None:
        values["mape"] = mape
    return values