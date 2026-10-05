"""Shared data loading and feature-selection contracts for Phase 4 models."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

FORECAST_TARGETS = ["next_hour_arrivals", "next_3hr_arrivals", "next_6hr_arrivals", "next_24hr_arrivals"]
RESOURCE_TARGETS = ["required_beds", "required_doctors", "required_nurses"]
NON_FEATURE_COLUMNS = {"timestamp", "congestion_level", *FORECAST_TARGETS, *RESOURCE_TARGETS}


def load_processed_splits(processed_dir: str | Path = "dataset/processed") -> dict[str, pd.DataFrame]:
    path = Path(processed_dir)
    return {name: pd.read_csv(path / f"{name}.csv") for name in ("training", "validation", "test")}


def feature_columns(data: pd.DataFrame) -> list[str]:
    return [column for column in data.select_dtypes(include="number").columns if column not in NON_FEATURE_COLUMNS]


def split_xy(data: pd.DataFrame, target: str, columns: list[str] | None = None) -> tuple[pd.DataFrame, pd.Series]:
    selected = columns or feature_columns(data)
    return data[selected].copy(), data[target].copy()