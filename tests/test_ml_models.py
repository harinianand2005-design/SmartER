from pathlib import Path

import joblib
import pandas as pd

from ml.training.common import feature_columns


ARTIFACT_DIR = Path("ml/models")
EXPECTED_ARTIFACTS = [
    "arrival_forecasting_1h.joblib", "arrival_forecasting_3h.joblib", "arrival_forecasting_6h.joblib", "arrival_forecasting_24h.joblib",
    "congestion_classifier.joblib", "bed_prediction_model.joblib", "doctor_prediction_model.joblib", "nurse_prediction_model.joblib",
]


def test_model_artifacts_exist_and_load():
    for filename in EXPECTED_ARTIFACTS:
        artifact = joblib.load(ARTIFACT_DIR / filename)
        assert artifact["feature_columns"]
        assert artifact["model"] is not None


def test_forecast_output_shapes_and_horizons():
    test = pd.read_csv("dataset/processed/test.csv")
    for horizon in (1, 3, 6, 24):
        artifact = joblib.load(ARTIFACT_DIR / f"arrival_forecasting_{horizon}h.joblib")
        predictions = artifact["model"].predict(test[artifact["feature_columns"]])
        assert len(predictions) == len(test)
        assert predictions.dtype.kind in "fiu"
        assert artifact["target"] == {1: "next_hour_arrivals", 3: "next_3hr_arrivals", 6: "next_6hr_arrivals", 24: "next_24hr_arrivals"}[horizon]


def test_classification_outputs_are_valid():
    test = pd.read_csv("dataset/processed/test.csv")
    artifact = joblib.load(ARTIFACT_DIR / "congestion_classifier.joblib")
    predictions = artifact["label_encoder"].inverse_transform(artifact["model"].predict(test[artifact["feature_columns"]]).astype(int))
    assert set(predictions).issubset({"NORMAL", "MODERATE", "HIGH", "CRITICAL"})
    assert len(predictions) == len(test)


def test_resource_outputs_are_numeric_and_non_negative():
    test = pd.read_csv("dataset/processed/test.csv")
    for filename in ("bed_prediction_model.joblib", "doctor_prediction_model.joblib", "nurse_prediction_model.joblib"):
        artifact = joblib.load(ARTIFACT_DIR / filename)
        predictions = artifact["model"].predict(test[artifact["feature_columns"]])
        assert predictions.dtype.kind in "fiu"
        assert (predictions >= 0).all()


def test_feature_compatibility_across_splits():
    training = pd.read_csv("dataset/processed/training.csv")
    validation = pd.read_csv("dataset/processed/validation.csv")
    test = pd.read_csv("dataset/processed/test.csv")
    columns = feature_columns(training)
    assert columns == feature_columns(validation) == feature_columns(test)