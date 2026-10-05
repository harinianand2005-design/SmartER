"""Artifact and metadata persistence helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib


def save_artifact(payload: Any, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, target)


def save_json(payload: Any, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def model_metadata(model_name: str, model_type: str, version: str, features: list[str], target: str, validation_metrics: dict, test_metrics: dict, hyperparameters: dict, training_range: tuple[str, str]) -> dict[str, Any]:
    return {"model_name": model_name, "model_type": model_type, "version": version, "training_date": datetime.now(timezone.utc).isoformat(), "feature_list": features, "target_variable": target, "validation_metrics": validation_metrics, "test_metrics": test_metrics, "hyperparameters": hyperparameters, "training_data_range": {"start": training_range[0], "end": training_range[1]}}