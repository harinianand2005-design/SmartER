"""Four-class ER congestion classification with validation-based model selection."""

from __future__ import annotations

import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.preprocessing import LabelEncoder

from ml.explainability.shap_utils import create_shap_summary
from ml.training.common import feature_columns, load_processed_splits
from ml.utils.artifacts import model_metadata, save_artifact, save_json


def classification_metrics(actual, predicted, labels: list[str]) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(actual, predicted, labels=labels, zero_division=0)
    class_metrics = {label: {"precision": float(p), "recall": float(r), "f1": float(score), "support": int(count)} for label, p, r, score, count in zip(labels, precision, recall, f1, support)}
    return {"accuracy": float(accuracy_score(actual, predicted)), "precision": float(precision_recall_fscore_support(actual, predicted, average="weighted", zero_division=0)[0]), "recall": float(precision_recall_fscore_support(actual, predicted, average="weighted", zero_division=0)[1]), "f1": float(f1_score(actual, predicted, average="weighted")), "class_metrics": class_metrics}


def _xgb_estimator(params: dict):
    try:
        from xgboost import XGBClassifier

        return XGBClassifier(objective="multi:softprob", eval_metric="mlogloss", random_state=42, n_jobs=4, **params)
    except ImportError:
        return None


def train_congestion_classifier(processed_dir: str | Path = "dataset/processed", artifact_dir: str | Path = "ml/models", output_dir: str | Path = "ml/evaluation/outputs", explainability_dir: str | Path = "ml/explainability/outputs") -> dict:
    splits = load_processed_splits(processed_dir)
    features = feature_columns(splits["training"])
    encoder = LabelEncoder().fit(splits["training"]["congestion_level"])
    labels = list(encoder.classes_)
    train = splits["training"]; validation = splits["validation"]; test = splits["test"]
    y_train = encoder.transform(train["congestion_level"])
    y_validation = encoder.transform(validation["congestion_level"])
    y_test = encoder.transform(test["congestion_level"])
    candidates = [("random_forest", RandomForestClassifier(n_estimators=140, max_depth=16, min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=-1))]
    xgb = _xgb_estimator({"n_estimators": 180, "max_depth": 5, "learning_rate": 0.08, "subsample": 0.9, "colsample_bytree": 0.9, "num_class": len(labels)})
    if xgb is not None:
        candidates.insert(0, ("xgboost", xgb))
    comparison = []
    fitted = {}
    for name, model in candidates:
        started = time.perf_counter(); model.fit(train[features], y_train); elapsed = time.perf_counter() - started
        predicted = encoder.inverse_transform(model.predict(validation[features]).astype(int))
        metrics = classification_metrics(validation["congestion_level"], predicted, labels)
        comparison.append({"model": name, "task": "congestion_classification", "validation_metrics": metrics, "test_metrics": None, "training_seconds": elapsed, "selected": False})
        fitted[name] = model
    best_row = max(comparison, key=lambda row: row["validation_metrics"]["f1"])
    best_row["selected"] = True
    best_model = fitted[best_row["model"]]
    test_prediction = best_model.predict(test[features]).astype(int)
    test_prediction_labels = encoder.inverse_transform(test_prediction)
    best_row["test_metrics"] = classification_metrics(test["congestion_level"], test_prediction_labels, labels)
    output_path = Path(output_dir); output_path.mkdir(parents=True, exist_ok=True)
    matrix = confusion_matrix(test["congestion_level"], test_prediction_labels, labels=labels)
    plt.figure(figsize=(7, 6)); plt.imshow(matrix, cmap="Blues"); plt.colorbar(); plt.xticks(range(len(labels)), labels, rotation=30); plt.yticks(range(len(labels)), labels); plt.xlabel("Predicted"); plt.ylabel("Actual"); plt.title("Congestion classification confusion matrix"); plt.tight_layout(); plt.savefig(output_path / "congestion_confusion_matrix.png", dpi=140); plt.close()
    model_name = "congestion_classifier"
    artifact = {"model": best_model, "label_encoder": encoder, "feature_columns": features, "classes": labels, "model_name": model_name}
    save_artifact(artifact, Path(artifact_dir) / f"{model_name}.joblib")
    metadata = model_metadata(model_name, best_row["model"], "1.0.0", features, "congestion_level", best_row["validation_metrics"], best_row["test_metrics"], best_model.get_params(), (str(train["timestamp"].iloc[0]), str(train["timestamp"].iloc[-1])))
    save_json(comparison, output_path / "classification_comparison.json")
    create_shap_summary(best_model, test, features, Path(explainability_dir) / "congestion_classifier_shap.json")
    return {"comparison": comparison, "metadata": metadata}