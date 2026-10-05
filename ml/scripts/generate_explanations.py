"""Generate optional SHAP contribution summaries from saved Phase 4 artifacts."""

from pathlib import Path

import joblib
import pandas as pd

from ml.explainability.shap_utils import create_shap_summary


def main() -> None:
    test = pd.read_csv("dataset/processed/test.csv")
    output = Path("ml/explainability/outputs")
    artifacts = ["congestion_classifier", "bed_prediction_model", "doctor_prediction_model", "nurse_prediction_model"]
    for name in artifacts:
        artifact = joblib.load(Path("ml/models") / f"{name}.joblib")
        create_shap_summary(artifact["model"], test, artifact["feature_columns"], output / f"{name}_shap.json")
    print(f"Generated {len(artifacts)} explainability summaries.")


if __name__ == "__main__":
    main()