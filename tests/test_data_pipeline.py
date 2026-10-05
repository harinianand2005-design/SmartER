import pandas as pd

from ml.data.generator import DEFAULT_COLUMNS, generate_dataset
from ml.data.validation import validate_dataframe
from ml.preprocessing.features import engineer_features
from ml.preprocessing.pipeline import DataPreprocessor, chronological_split


def test_generator_is_reproducible_and_has_required_columns():
    first = generate_dataset(periods=72, seed=7)
    second = generate_dataset(periods=72, seed=7)
    pd.testing.assert_frame_equal(first, second)
    assert list(first.columns) == DEFAULT_COLUMNS
    assert (first["patient_arrivals"] >= 0).all()


def test_validation_reports_invalid_rows():
    data = generate_dataset(periods=72)
    data.loc[0, "patient_arrivals"] = -1
    data["timestamp"] = data["timestamp"].astype(object)
    data.loc[1, "timestamp"] = "not-a-timestamp"
    report = validate_dataframe(data)
    assert report["valid"] is False
    assert report["checks"]["invalid_timestamps"] == 1
    assert report["checks"]["negative_values"]["patient_arrivals"] == 1


def test_validation_reports_invalid_types_and_categories():
    data = generate_dataset(periods=72)
    data["rainfall"] = data["rainfall"].astype(object)
    data.loc[0, "rainfall"] = "unknown"
    data.loc[1, "weather_category"] = "hail"
    data.loc[2, "holiday"] = 2
    report = validate_dataframe(data)
    assert report["valid"] is False
    assert report["checks"]["invalid_data_types"]["rainfall"] == 1
    assert report["checks"]["invalid_categorical_values"] == ["hail"]
    assert report["checks"]["invalid_binary_flags"]["holiday"] == 1


def test_preprocessor_handles_missing_values():
    data = generate_dataset(periods=72)
    data.loc[0, "temperature"] = None
    preprocessor = DataPreprocessor().fit(data.iloc[10:])
    transformed = preprocessor.transform(data)
    assert transformed["temperature"].isna().sum() == 0


def test_feature_engineering_is_ordered_and_past_only():
    data = engineer_features(generate_dataset(periods=96))
    assert data["timestamp"].is_monotonic_increasing
    assert data.loc[25, "previous_1hr_arrivals"] == data.loc[24, "patient_arrivals"]
    assert {"occupancy_percentage", "event_indicator", "next_24hr_arrivals"}.issubset(data.columns)


def test_chronological_split_has_no_overlap():
    data = engineer_features(generate_dataset(periods=120)).dropna()
    splits = chronological_split(data)
    assert len(splits["training"]) > len(splits["validation"]) > 0
    assert splits["training"]["timestamp"].max() < splits["validation"]["timestamp"].min()
    assert splits["validation"]["timestamp"].max() < splits["test"]["timestamp"].min()