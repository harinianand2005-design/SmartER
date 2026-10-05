"""Arrival forecasting benchmarks and supervised forecasting models."""

from __future__ import annotations

import time
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

from ml.training.common import FORECAST_TARGETS, feature_columns, load_processed_splits
from ml.training.metrics import regression_metrics
from ml.utils.artifacts import model_metadata, save_artifact, save_json

HORIZONS = {1: "next_hour_arrivals", 3: "next_3hr_arrivals", 6: "next_6hr_arrivals", 24: "next_24hr_arrivals"}
BASELINE_FEATURES = {1: "previous_1hr_arrivals", 3: "previous_3hr_arrivals", 6: "previous_6hr_arrivals", 24: "previous_24hr_arrivals"}


def _estimator(name: str, params: dict):
    if name == "gradient_boosting":
        return GradientBoostingRegressor(random_state=42, **params)
    return RandomForestRegressor(random_state=42, n_jobs=-1, **params)


def _plot_forecast(actual: pd.Series, predicted: pd.Series, horizon: int, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sample = min(500, len(actual))
    plt.figure(figsize=(12, 4)); plt.plot(actual.iloc[:sample].to_numpy(), label="actual"); plt.plot(predicted.iloc[:sample].to_numpy(), label="predicted"); plt.title(f"Arrival forecast: next {horizon} hour(s)"); plt.legend(); plt.tight_layout(); plt.savefig(output_dir / f"arrival_actual_vs_predicted_{horizon}h.png", dpi=140); plt.close()
    errors = actual.iloc[:sample].to_numpy() - predicted.iloc[:sample].to_numpy()
    plt.figure(figsize=(12, 3)); plt.plot(errors); plt.axhline(0, color="black", linewidth=1); plt.title(f"Arrival forecast error: next {horizon} hour(s)"); plt.tight_layout(); plt.savefig(output_dir / f"arrival_prediction_error_{horizon}h.png", dpi=140); plt.close()


def train_forecasting_models(processed_dir: str | Path = "dataset/processed", artifact_dir: str | Path = "ml/models", output_dir: str | Path = "ml/evaluation/outputs") -> dict:
    splits = load_processed_splits(processed_dir)
    features = feature_columns(splits["training"])
    artifact_path = Path(artifact_dir); output_path = Path(output_dir)
    comparison: list[dict] = []
    metadata: list[dict] = []
    configs = {
        "gradient_boosting": {"n_estimators": 120, "learning_rate": 0.05, "max_depth": 3, "min_samples_leaf": 5},
        "random_forest": {"n_estimators": 100, "max_depth": 14, "min_samples_leaf": 2},
    }
    for horizon, target in HORIZONS.items():
        train = splits["training"]; validation = splits["validation"]; test = splits["test"]
        baseline_validation = validation[BASELINE_FEATURES[horizon]].fillna(train[BASELINE_FEATURES[horizon]].median()).clip(lower=0)
        baseline_test = test[BASELINE_FEATURES[horizon]].fillna(train[BASELINE_FEATURES[horizon]].median()).clip(lower=0)
        comparison.extend([
            {"model": "seasonal_naive", "task": "arrival_forecasting", "target": target, "validation_metrics": regression_metrics(validation[target], baseline_validation), "test_metrics": regression_metrics(test[target], baseline_test), "training_seconds": 0.0, "selected": False},
        ])
        try:
            from statsmodels.tsa.arima.model import ARIMA

            arima_started = time.perf_counter()
            arima_validation_model = ARIMA(train[target].astype(float), order=(1, 0, 0), enforce_stationarity=False, enforce_invertibility=False).fit()
            arima_validation_pred = pd.Series(arima_validation_model.forecast(len(validation)), index=validation.index).clip(lower=0)
            if not arima_validation_pred.notna().all():
                raise ValueError("ARIMA produced non-finite validation forecasts")
            arima_validation_metrics = regression_metrics(validation[target], arima_validation_pred)
            arima_test_model = ARIMA(pd.concat([train[target], validation[target]]).astype(float), order=(1, 0, 0), enforce_stationarity=False, enforce_invertibility=False).fit()
            arima_test_pred = pd.Series(arima_test_model.forecast(len(test)), index=test.index).clip(lower=0)
            if not arima_test_pred.notna().all():
                raise ValueError("ARIMA produced non-finite test forecasts")
            comparison.append({"model": "arima_1_0_0", "task": "arrival_forecasting", "target": target, "validation_metrics": arima_validation_metrics, "test_metrics": regression_metrics(test[target], arima_test_pred), "training_seconds": time.perf_counter() - arima_started, "selected": False, "parameters_tested": {"order": [(1, 0, 0)]}})
        except Exception as error:
            comparison.append({"model": "arima_1_0_0", "task": "arrival_forecasting", "target": target, "validation_metrics": None, "test_metrics": None, "training_seconds": 0.0, "selected": False, "available": False, "reason": str(error)})
        best_name = ""; best_model = None; best_params = {}; best_validation = None; best_elapsed = 0.0
        for name, params in configs.items():
            started = time.perf_counter()
            model = _estimator(name, params)
            model.fit(train[features], train[target])
            validation_pred = pd.Series(model.predict(validation[features]), index=validation.index).clip(lower=0)
            validation_metrics = regression_metrics(validation[target], validation_pred)
            elapsed = time.perf_counter() - started
            comparison.append({"model": name, "task": "arrival_forecasting", "target": target, "validation_metrics": validation_metrics, "test_metrics": None, "training_seconds": elapsed, "selected": False})
            if best_validation is None or validation_metrics["mae"] < best_validation["mae"]:
                best_name, best_model, best_params, best_validation, best_elapsed = name, model, params, validation_metrics, elapsed
        selected = next(row for row in comparison if row["target"] == target and row["model"] == best_name)
        selected["selected"] = True
        test_pred = pd.Series(best_model.predict(test[features]), index=test.index).clip(lower=0)
        selected["test_metrics"] = regression_metrics(test[target], test_pred)
        model_name = f"arrival_forecasting_{horizon}h"
        save_artifact({"model": best_model, "feature_columns": features, "target": target, "model_name": model_name}, artifact_path / f"{model_name}.joblib")
        metadata.append(model_metadata(model_name, best_name, "1.0.0", features, target, best_validation, selected["test_metrics"], best_params, (str(train["timestamp"].iloc[0]), str(train["timestamp"].iloc[-1]))))
        _plot_forecast(test[target], test_pred, horizon, output_path)
    save_json(comparison, output_path / "forecasting_comparison.json")
    return {"comparison": comparison, "metadata": metadata}


def load_forecasting_artifact(path: str | Path):
    return joblib.load(path)