"""Resource requirement regression for beds, doctors, and nurses."""

from __future__ import annotations

import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from ml.explainability.shap_utils import create_shap_summary
from ml.training.common import RESOURCE_TARGETS, feature_columns, load_processed_splits
from ml.training.metrics import regression_metrics
from ml.utils.artifacts import model_metadata, save_artifact, save_json


def _xgb_estimator(params: dict):
    try:
        from xgboost import XGBRegressor

        return XGBRegressor(objective="reg:squarederror", random_state=42, n_jobs=4, **params)
    except ImportError:
        return None


def _plot_resource(actual: pd.Series, predicted: pd.Series, target: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sample = min(500, len(actual)); plt.figure(figsize=(12, 4)); plt.plot(actual.iloc[:sample].to_numpy(), label="actual"); plt.plot(predicted.iloc[:sample].to_numpy(), label="predicted"); plt.title(f"{target} resource prediction"); plt.legend(); plt.tight_layout(); plt.savefig(output_dir / f"{target}_actual_vs_predicted.png", dpi=140); plt.close()


def train_resource_models(processed_dir: str | Path = "dataset/processed", artifact_dir: str | Path = "ml/models", output_dir: str | Path = "ml/evaluation/outputs", explainability_dir: str | Path = "ml/explainability/outputs") -> dict:
    splits = load_processed_splits(processed_dir)
    features = feature_columns(splits["training"])
    comparison = []; metadata = []
    for target in RESOURCE_TARGETS:
        train = splits["training"]; validation = splits["validation"]; test = splits["test"]
        candidates = [("linear_regression", LinearRegression()), ("random_forest", RandomForestRegressor(n_estimators=120, max_depth=16, min_samples_leaf=2, random_state=42, n_jobs=-1))]
        xgb = _xgb_estimator({"n_estimators": 180, "max_depth": 5, "learning_rate": 0.08, "subsample": 0.9, "colsample_bytree": 0.9})
        if xgb is not None:
            candidates.append(("xgboost", xgb))
        fitted = {}
        for name, model in candidates:
            started = time.perf_counter(); model.fit(train[features], train[target]); elapsed = time.perf_counter() - started
            validation_pred = pd.Series(model.predict(validation[features]), index=validation.index).clip(lower=0)
            validation_metrics = regression_metrics(validation[target], validation_pred)
            comparison.append({"model": name, "task": "resource_prediction", "target": target, "validation_metrics": validation_metrics, "test_metrics": None, "training_seconds": elapsed, "selected": False})
            fitted[name] = model
        target_rows = [row for row in comparison if row["target"] == target]
        best_row = min(target_rows, key=lambda row: row["validation_metrics"]["mae"]); best_row["selected"] = True
        best_model = fitted[best_row["model"]]
        test_pred = pd.Series(best_model.predict(test[features]), index=test.index).clip(lower=0)
        best_row["test_metrics"] = regression_metrics(test[target], test_pred)
        model_name = {"required_beds": "bed_prediction_model", "required_doctors": "doctor_prediction_model", "required_nurses": "nurse_prediction_model"}[target]
        save_artifact({"model": best_model, "feature_columns": features, "target": target, "model_name": model_name}, Path(artifact_dir) / f"{model_name}.joblib")
        metadata.append(model_metadata(model_name, best_row["model"], "1.0.0", features, target, best_row["validation_metrics"], best_row["test_metrics"], best_model.get_params(), (str(train["timestamp"].iloc[0]), str(train["timestamp"].iloc[-1]))))
        _plot_resource(test[target], test_pred, target, Path(output_dir))
        create_shap_summary(best_model, test, features, Path(explainability_dir) / f"{model_name}_shap.json")
    save_json(comparison, Path(output_dir) / "resource_comparison.json")
    return {"comparison": comparison, "metadata": metadata}