from pathlib import Path

import joblib
import pandas as pd


ARTIFACTS = [
    "arrival_forecasting_1h.joblib", "arrival_forecasting_3h.joblib", "arrival_forecasting_6h.joblib", "arrival_forecasting_24h.joblib",
    "congestion_classifier.joblib", "bed_prediction_model.joblib", "doctor_prediction_model.joblib", "nurse_prediction_model.joblib",
]


def test_phase4_artifacts_load_and_have_compatible_features():
    training = pd.read_csv("dataset/processed/training.csv")
    feature_columns = set(training.select_dtypes(include="number").columns) - {"next_hour_arrivals", "next_3hr_arrivals", "next_6hr_arrivals", "next_24hr_arrivals", "required_beds", "required_doctors", "required_nurses"}
    for filename in ARTIFACTS:
        artifact = joblib.load(Path("ml/models") / filename)
        assert set(artifact["feature_columns"]) == feature_columns


def test_forecasting_horizons_and_prediction_types():
    test = pd.read_csv("dataset/processed/test.csv")
    for horizon in (1, 3, 6, 24):
        artifact = joblib.load(Path("ml/models") / f"arrival_forecasting_{horizon}h.joblib")
        predictions = artifact["model"].predict(test[artifact["feature_columns"]])
        assert predictions.shape == (len(test),)
        assert predictions.dtype.kind in "fiu"


def test_classification_and_resource_prediction_outputs():
    test = pd.read_csv("dataset/processed/test.csv")
    classifier = joblib.load(Path("ml/models/congestion_classifier.joblib"))
    labels = classifier["label_encoder"].inverse_transform(classifier["model"].predict(test[classifier["feature_columns"]]).astype(int))
    assert set(labels).issubset({"NORMAL", "MODERATE", "HIGH", "CRITICAL"})
    for filename in ("bed_prediction_model.joblib", "doctor_prediction_model.joblib", "nurse_prediction_model.joblib"):
        artifact = joblib.load(Path("ml/models") / filename)
        values = artifact["model"].predict(test[artifact["feature_columns"]])
        assert values.shape == (len(test),)
        assert (values >= 0).all()