"""Reusable data-quality checks for the synthetic ER dataset."""

from __future__ import annotations

from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {
    "timestamp", "patient_arrivals", "current_patients", "available_beds", "doctors_available",
    "nurses_available", "average_waiting_time", "triage_1", "triage_2", "triage_3", "triage_4",
    "triage_5", "temperature", "rainfall", "holiday", "local_event", "flu_index", "weather_category",
    "doctors_scheduled", "nurses_scheduled",
}
VALID_WEATHER_CATEGORIES = {"clear", "rain", "storm"}


def validate_dataframe(data: pd.DataFrame) -> dict[str, Any]:
    """Return a transparent validation report without silently changing data."""
    report: dict[str, Any] = {"row_count": int(len(data)), "column_count": int(len(data.columns)), "checks": {}, "valid": True}
    missing_columns = sorted(REQUIRED_COLUMNS - set(data.columns))
    report["checks"]["required_columns"] = {"valid": not missing_columns, "missing": missing_columns}
    if missing_columns:
        report["valid"] = False
        return report

    timestamps = pd.to_datetime(data["timestamp"], errors="coerce", utc=True)
    numeric_non_negative = ["patient_arrivals", "current_patients", "available_beds", "doctors_available", "nurses_available", "average_waiting_time", "triage_1", "triage_2", "triage_3", "triage_4", "triage_5", "rainfall", "flu_index", "doctors_scheduled", "nurses_scheduled"]
    numeric_values = {column: pd.to_numeric(data[column], errors="coerce") for column in numeric_non_negative}
    invalid_numeric_types = {column: int(numeric_values[column].isna().sum() - data[column].isna().sum()) for column in numeric_non_negative}
    negative_counts = {column: int((numeric_values[column] < 0).sum()) for column in numeric_non_negative}
    triage_values = pd.concat([numeric_values[f"triage_{level}"] for level in range(1, 6)], axis=1)
    invalid_triage = int((triage_values.sum(axis=1) != numeric_values["patient_arrivals"]).sum())
    capacity = numeric_values["current_patients"] + numeric_values["available_beds"]
    occupancy = numeric_values["current_patients"] / capacity.replace(0, 1) * 100
    checks = {
        "missing_values": {column: int(value) for column, value in data.isna().sum().items() if value},
        "duplicate_rows": int(data.duplicated().sum()),
        "invalid_timestamps": int(timestamps.isna().sum()),
        "negative_values": negative_counts,
        "invalid_data_types": invalid_numeric_types,
        "invalid_resource_counts": int(((numeric_values["doctors_available"] > numeric_values["doctors_scheduled"]) | (numeric_values["nurses_available"] > numeric_values["nurses_scheduled"])).sum()),
        "invalid_waiting_times": int((numeric_values["average_waiting_time"] > 24 * 60).sum()),
        "invalid_triage_counts": invalid_triage,
        "impossible_occupancy": int(((occupancy < 0) | (occupancy > 100)).sum()),
        "invalid_categorical_values": sorted(set(data["weather_category"].dropna()) - VALID_WEATHER_CATEGORIES),
        "invalid_binary_flags": {column: int((~data[column].isin([0, 1])).sum()) for column in ["holiday", "local_event"]},
    }
    report["checks"].update(checks)
    report["valid"] = not any([
        bool(missing_columns), checks["missing_values"], checks["duplicate_rows"], checks["invalid_timestamps"],
        any(negative_counts.values()), any(invalid_numeric_types.values()), checks["invalid_resource_counts"], checks["invalid_waiting_times"],
        checks["invalid_triage_counts"], checks["impossible_occupancy"], checks["invalid_categorical_values"], any(checks["invalid_binary_flags"].values()),
    ])
    return report