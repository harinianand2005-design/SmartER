
"""Lazy Phase 4 artifact loading and feature-compatible inference."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.core.config import get_settings
from app.schemas.predictions import ERPredictionInput


class ModelServiceError(RuntimeError):
    """Raised when a persisted model cannot be loaded or used safely."""


MODEL_NAMES = {
    "forecast_1h": "arrival_forecasting_1h",
    "forecast_3h": "arrival_forecasting_3h",
    "forecast_6h": "arrival_forecasting_6h",
    "forecast_24h": "arrival_forecasting_24h",
    "congestion": "congestion_classifier",
    "beds": "bed_prediction_model",
    "doctors": "doctor_prediction_model",
    "nurses": "nurse_prediction_model",
}


class ModelService:
    def __init__(self) -> None:
        settings = get_settings()
        root = Path(__file__).resolve().parents[3]

        configured = Path(settings.ml_models_dir)
        self.models_dir = (
            configured if configured.is_absolute()
            else root / configured
        )

        metadata_path = Path(settings.ml_metadata_path)
        self.metadata_path = (
            metadata_path if metadata_path.is_absolute()
            else root / metadata_path
        )

        self._models: dict[str, dict[str, Any]] = {}
        self._metadata = self._read_metadata()

    def _read_metadata(self) -> dict[str, dict]:
        try:
            rows = json.loads(
                self.metadata_path.read_text(encoding="utf-8")
            )
            return {row["model_name"]: row for row in rows}
        except (OSError, ValueError, KeyError):
            return {}

    def _load(self, key: str) -> dict[str, Any]:
        if key in self._models:
            return self._models[key]

        model_name = MODEL_NAMES[key]
        path = self.models_dir / f"{model_name}.joblib"

        try:
            artifact = joblib.load(path)

            if (
                not artifact.get("feature_columns")
                or artifact.get("model") is None
            ):
                raise ModelServiceError(
                    f"Invalid artifact contract for {model_name}"
                )

            metadata = self._metadata.get(model_name, {})
            expected = metadata.get("feature_list")

            if expected and artifact["feature_columns"] != expected:
                raise ModelServiceError(
                    f"Feature order mismatch for {model_name}"
                )

            loaded = {
                "artifact": artifact,
                "metadata": metadata,
                "path": path,
            }
            self._models[key] = loaded
            return loaded

        except ModelServiceError:
            raise
        except Exception as error:
            raise ModelServiceError(
                f"Unable to load {model_name}: {error}"
            ) from error

    def status(self) -> list[dict]:
        result = []

        for key, model_name in MODEL_NAMES.items():
            metadata = self._metadata.get(model_name, {})

            try:
                loaded = self._load(key)
                result.append({
                    "model_name": model_name,
                    "version": metadata.get("version"),
                    "loaded": True,
                    "artifact_name": loaded["path"].name,
                    "validation_metrics": metadata.get(
                        "validation_metrics"
                    ),
                    "test_metrics": metadata.get("test_metrics"),
                })

            except ModelServiceError as error:
                result.append({
                    "model_name": model_name,
                    "version": metadata.get("version"),
                    "loaded": False,
                    "artifact_name": f"{model_name}.joblib",
                    "validation_metrics": metadata.get(
                        "validation_metrics"
                    ),
                    "test_metrics": metadata.get("test_metrics"),
                    "error": str(error),
                })

        return result

    @staticmethod
    def _features(
        payload: ERPredictionInput,
        feature_names: list[str],
    ) -> pd.DataFrame:
        row = payload.model_dump()
        row["timestamp"] = pd.Timestamp(payload.timestamp)
        row["weather_category"] = payload.weather_category.value

        frame = pd.DataFrame([row])
        timestamp = pd.to_datetime(frame["timestamp"], utc=True)
        arrivals = frame["patient_arrivals"]

        frame["hour"] = timestamp.dt.hour
        frame["day_of_week"] = timestamp.dt.dayofweek
        frame["day_of_month"] = timestamp.dt.day
        frame["month"] = timestamp.dt.month
        frame["is_weekend"] = (
            frame["day_of_week"] >= 5
        ).astype(int)

        frame["is_holiday"] = frame["holiday"]
        frame["previous_1hr_arrivals"] = arrivals

        for hours in (3, 6, 24):
            frame[f"previous_{hours}hr_arrivals"] = arrivals * hours
            frame[f"rolling_{hours}hr_average"] = arrivals

        capacity = (
            frame["current_patients"] + frame["available_beds"]
        ).replace(0, 1)

        frame["occupancy_percentage"] = (
            frame["current_patients"] / capacity * 100
        ).clip(0, 100)

        frame["bed_availability_percentage"] = (
            frame["available_beds"] / capacity * 100
        ).clip(0, 100)

        frame["doctor_availability_percentage"] = (
            frame["doctors_available"]
            / frame["doctors_scheduled"].replace(0, 1)
            * 100
        ).clip(0, 100)

        frame["nurse_availability_percentage"] = (
            frame["nurses_available"]
            / frame["nurses_scheduled"].replace(0, 1)
            * 100
        ).clip(0, 100)

        frame["event_indicator"] = (
            (frame["holiday"] == 1)
            | (frame["local_event"] == 1)
        ).astype(int)

        frame["rainy_flag"] = (frame["rainfall"] >= 2).astype(int)
        frame["flu_index_change_24hr"] = 0.0

        for category in ("clear", "rain", "storm"):
            frame[f"weather_category_{category}"] = (
                frame["weather_category"] == category
            ).astype(int)

        missing = [
            name for name in feature_names
            if name not in frame.columns
        ]

        if missing:
            raise ModelServiceError(
                f"Missing inference features: {missing}"
            )

        return frame[feature_names].apply(
            pd.to_numeric, errors="coerce"
        ).fillna(0.0)

    def _predict(self, key: str, payload: ERPredictionInput):
        loaded = self._load(key)
        artifact = loaded["artifact"]

        features = self._features(
            payload, artifact["feature_columns"]
        )

        prediction = artifact["model"].predict(features)[0]
        return loaded, features, prediction

    def forecast(self, payload: ERPredictionInput) -> dict:
        values = {}
        versions = []

        for horizon, key in (
            (1, "forecast_1h"),
            (3, "forecast_3h"),
            (6, "forecast_6h"),
            (24, "forecast_24h"),
        ):
            loaded, _, value = self._predict(key, payload)

            values[f"{horizon}h"] = max(0.0, float(value))
            versions.append(
                loaded["metadata"].get("version", "unknown")
            )

        return {
            "timestamp": payload.timestamp,
            "forecasts": values,
            "model_version": ",".join(sorted(set(versions))),
        }

    def congestion(self, payload: ERPredictionInput) -> dict:
        loaded, features, raw_prediction = self._predict(
            "congestion", payload
        )

        artifact = loaded["artifact"]
        encoder = artifact["label_encoder"]

        label = str(
            encoder.inverse_transform([int(raw_prediction)])[0]
        )

        probabilities = artifact["model"].predict_proba(features)[0]
        classes = [str(item) for item in encoder.classes_]

        probability_map = {
            name: float(value)
            for name, value in zip(classes, probabilities)
        }

        return {
            "timestamp": payload.timestamp,
            "congestion_level": label,
            "probabilities": probability_map,
            "confidence": max(probability_map.values()),
            "model_version": loaded["metadata"].get(
                "version", "unknown"
            ),
        }

    def resources(self, payload: ERPredictionInput) -> dict:
        predictions = {}
        versions = {}

        for target, key in (
            ("required_beds", "beds"),
            ("required_doctors", "doctors"),
            ("required_nurses", "nurses"),
        ):
            loaded, _, value = self._predict(key, payload)

            predictions[target] = max(0.0, float(value))
            versions[target] = loaded["metadata"].get(
                "version", "unknown"
            )

        return {
            "timestamp": payload.timestamp,
            **predictions,
            "model_versions": versions,
        }


@lru_cache
def get_model_service() -> ModelService:
    return ModelService()
