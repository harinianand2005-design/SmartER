"""Leakage-aware preprocessing and chronological dataset preparation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ml.data.validation import validate_dataframe
from ml.preprocessing.features import engineer_features


class DataPreprocessor:
    """Fit missing-value and categorical transforms on training data only."""

    def __init__(self) -> None:
        self.numeric_medians: dict[str, float] = {}
        self.categorical_modes: dict[str, str] = {}
        self.categorical_levels: dict[str, list[str]] = {}

    def fit(self, data: pd.DataFrame) -> "DataPreprocessor":
        numeric = data.select_dtypes(include="number").columns
        self.numeric_medians = {column: float(data[column].median()) for column in numeric}
        categorical = data.select_dtypes(include=["object", "category"]).columns
        self.categorical_modes = {column: str(data[column].mode(dropna=True).iloc[0]) if not data[column].mode(dropna=True).empty else "unknown" for column in categorical}
        self.categorical_levels = {column: sorted(data[column].dropna().astype(str).unique().tolist()) for column in categorical}
        return self

    def transform(self, data: pd.DataFrame, preserve_categoricals: set[str] | None = None) -> pd.DataFrame:
        result = data.copy()
        preserve_categoricals = preserve_categoricals or set()
        for column, median in self.numeric_medians.items():
            if column in result:
                result[column] = pd.to_numeric(result[column], errors="coerce").fillna(median)
        for column, mode in self.categorical_modes.items():
            if column in preserve_categoricals:
                result[column] = result[column].fillna(mode)
                continue
            if column in result:
                result[column] = result[column].astype(str).replace("nan", mode).fillna(mode)
                for level in self.categorical_levels[column]:
                    result[f"{column}_{level}"] = (result[column] == level).astype(int)
                result = result.drop(columns=[column])
        return result


def chronological_split(data: pd.DataFrame, train_ratio: float = 0.70, validation_ratio: float = 0.15) -> dict[str, pd.DataFrame]:
    if not 0 < train_ratio < 1 or not 0 < validation_ratio < 1 or train_ratio + validation_ratio >= 1:
        raise ValueError("train_ratio and validation_ratio must leave a positive test portion")
    ordered = data.sort_values("timestamp").reset_index(drop=True)
    train_end = int(len(ordered) * train_ratio)
    validation_end = train_end + int(len(ordered) * validation_ratio)
    return {"training": ordered.iloc[:train_end].copy(), "validation": ordered.iloc[train_end:validation_end].copy(), "test": ordered.iloc[validation_end:].copy()}


def prepare_dataset(input_path: str | Path, output_dir: str | Path) -> dict[str, object]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(input_path)
    validation_before = validate_dataframe(raw)
    cleaned = raw.drop_duplicates().copy()
    cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], errors="coerce", utc=True)
    cleaned = cleaned.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    engineered = engineer_features(cleaned).dropna(subset=["next_hour_arrivals", "next_3hr_arrivals", "next_6hr_arrivals", "next_24hr_arrivals", "congestion_level"]).reset_index(drop=True)
    splits = chronological_split(engineered)
    preprocessor = DataPreprocessor().fit(splits["training"])
    transformed = {name: preprocessor.transform(frame, preserve_categoricals={"congestion_level"}) for name, frame in splits.items()}
    for name, frame in transformed.items():
        frame.to_csv(output_path / f"{name}.csv", index=False)
    report = {"before_cleaning": validation_before, "rows_after_cleaning": len(cleaned), "split_rows": {name: len(frame) for name, frame in transformed.items()}, "split_strategy": "chronological 70% training, 15% validation, 15% test; no shuffle", "feature_fit_scope": "training split only"}
    (output_path / "validation_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (output_path / "preprocessing_metadata.json").write_text(json.dumps({"numeric_medians": preprocessor.numeric_medians, "categorical_levels": preprocessor.categorical_levels}, indent=2), encoding="utf-8")
    return report