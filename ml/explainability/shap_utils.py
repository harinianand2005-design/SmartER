"""Prepare feature-contribution summaries for later SHAP UI integration."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml.utils.artifacts import save_json


def create_shap_summary(model, data: pd.DataFrame, feature_names: list[str], output_path: str | Path, sample_size: int = 500) -> dict:
    """Save mean absolute SHAP contributions; these are model contributions, not causation."""
    try:
        import shap

        sample = data[feature_names].sample(min(sample_size, len(data)), random_state=42)
        try:
            explainer = shap.TreeExplainer(model)
            values = explainer(sample)
        except Exception:
            explainer = shap.Explainer(model.predict, sample)
            values = explainer(sample)
        raw_values = values.values
        if raw_values.ndim == 3:
            raw_values = abs(raw_values).mean(axis=2)
        importance = abs(raw_values).mean(axis=0)
        summary = {"available": True, "interpretation": "Features contributing to the model prediction; not medical causation.", "features": sorted(({"feature": name, "mean_absolute_shap": float(value)} for name, value in zip(feature_names, importance)), key=lambda item: item["mean_absolute_shap"], reverse=True)}
    except Exception as error:  # Optional explainability should not block training.
        summary = {"available": False, "reason": str(error), "interpretation": "SHAP was not available for this artifact."}
    save_json(summary, output_path)
    return summary