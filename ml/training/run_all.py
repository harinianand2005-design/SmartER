"""Train and evaluate every Phase 4 model without touching prediction APIs."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ml.explainability.shap_utils import create_shap_summary
from ml.training.classification import train_congestion_classifier
from ml.training.common import load_processed_splits
from ml.training.forecasting import train_forecasting_models
from ml.training.resources import train_resource_models
from ml.utils.artifacts import save_json
from ml.preprocessing.features import FEATURE_DESCRIPTIONS


def run_training(processed_dir: str | Path = "dataset/processed", artifact_dir: str | Path = "ml/models", evaluation_dir: str | Path = "ml/evaluation/outputs") -> dict:
    artifact_path = Path(artifact_dir); evaluation_path = Path(evaluation_dir)
    explainability_path = Path("ml/explainability/outputs")
    splits = load_processed_splits(processed_dir)
    forecast = train_forecasting_models(processed_dir, artifact_path, evaluation_path)
    classification = train_congestion_classifier(processed_dir, artifact_path, evaluation_path, explainability_path)
    resources = train_resource_models(processed_dir, artifact_path, evaluation_path, explainability_path)
    all_metadata = forecast["metadata"] + [classification["metadata"]] + resources["metadata"]
    comparison = forecast["comparison"] + classification["comparison"] + resources["comparison"]
    save_json(all_metadata, artifact_path / "model_metadata.json")
    for item in all_metadata:
        model_dir = artifact_path / item["model_name"]
        model_dir.mkdir(parents=True, exist_ok=True)
        root_artifact = artifact_path / f"{item['model_name']}.joblib"
        versioned_artifact = model_dir / f"{item['model_name']}_v{item['version']}.joblib"
        if root_artifact.exists():
            shutil.copy2(root_artifact, versioned_artifact)
        item["artifact_path"] = str(versioned_artifact)
        save_json(item, model_dir / "metadata.json")
        (model_dir / "README.md").write_text("Academic decision-support model artifact. Not a medical diagnosis or autonomous clinical decision.\n", encoding="utf-8")
    save_json(all_metadata, artifact_path / "model_metadata.json")
    save_json({"features": FEATURE_DESCRIPTIONS, "model_input_columns": forecast["metadata"][0]["feature_list"]}, artifact_path / "feature_metadata.json")
    save_json(comparison, evaluation_path / "model_comparison.json")
    save_json({"forecasting": {"tested": ["seasonal_naive", "arima_1_0_0", "gradient_boosting", "random_forest"], "selection_metric": "validation MAE"}, "classification": {"tested": [row["model"] for row in classification["comparison"]], "selection_metric": "validation weighted F1"}, "resources": {"tested": sorted({row["model"] for row in resources["comparison"]}), "selection_metric": "validation MAE"}}, artifact_path / "tuning_reports.json")
    summary = {"Phase4_complete": True, "models": [item["model_name"] for item in all_metadata], "features_used": all_metadata[0]["feature_list"], "training_rows": len(splits["training"]), "validation_rows": len(splits["validation"]), "test_rows": len(splits["test"]), "test_evaluation_policy": "Selected models were chosen using validation metrics; test metrics were calculated once after selection.", "api_or_dashboard_changes": False, "safety_boundary": "Academic decision-support predictions only; not medical diagnoses or autonomous clinical decisions."}
    save_json(summary, artifact_path / "training_summary.json")
    return {"metadata": all_metadata, "comparison": comparison, "summary": summary}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SmartER Phase 4 models")
    parser.add_argument("--processed-dir", default="dataset/processed")
    parser.add_argument("--artifact-dir", default="ml/models")
    parser.add_argument("--evaluation-dir", default="ml/evaluation/outputs")
    args = parser.parse_args()
    result = run_training(args.processed_dir, args.artifact_dir, args.evaluation_dir)
    print(result["summary"])