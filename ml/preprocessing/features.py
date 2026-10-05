"""Past-only feature engineering and future target preparation."""

from __future__ import annotations

import pandas as pd


FEATURE_DESCRIPTIONS = {
    "hour": "Hour of day in UTC, capturing intraday demand cycles.",
    "day_of_week": "Monday=0 through Sunday=6.",
    "day_of_month": "Calendar day number.",
    "month": "Calendar month number for seasonal effects.",
    "is_weekend": "Whether the timestamp falls on Saturday or Sunday.",
    "is_holiday": "Holiday indicator copied from the synthetic calendar.",
    "previous_1hr_arrivals": "Arrivals in the immediately preceding hour.",
    "previous_3hr_arrivals": "Total arrivals in the three preceding hours.",
    "previous_6hr_arrivals": "Total arrivals in the six preceding hours.",
    "previous_24hr_arrivals": "Total arrivals in the 24 preceding hours.",
    "rolling_3hr_average": "Mean arrivals across the three preceding hours.",
    "rolling_6hr_average": "Mean arrivals across the six preceding hours.",
    "rolling_24hr_average": "Mean arrivals across the 24 preceding hours.",
    "occupancy_percentage": "Current patients as a percentage of observed bed capacity.",
    "bed_availability_percentage": "Available beds as a percentage of observed bed capacity.",
    "doctor_availability_percentage": "Available doctors as a percentage of scheduled doctors.",
    "nurse_availability_percentage": "Available nurses as a percentage of scheduled nurses.",
    "event_indicator": "1 when a holiday or local event is active, otherwise 0.",
    "rainy_flag": "1 when rainfall is at least 2 mm in the hour.",
    "flu_index_change_24hr": "Change in synthetic flu index from 24 hours earlier.",
}


def engineer_features(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True)
    result = result.sort_values("timestamp").reset_index(drop=True)
    timestamp = result["timestamp"]
    arrivals = result["patient_arrivals"]
    result["hour"] = timestamp.dt.hour
    result["day_of_week"] = timestamp.dt.dayofweek
    result["day_of_month"] = timestamp.dt.day
    result["month"] = timestamp.dt.month
    result["is_weekend"] = (result["day_of_week"] >= 5).astype(int)
    result["is_holiday"] = result["holiday"].astype(int)
    prior = arrivals.shift(1)
    for hours in (3, 6, 24):
        result[f"previous_{hours}hr_arrivals"] = prior.rolling(hours, min_periods=1).sum()
        result[f"rolling_{hours}hr_average"] = prior.rolling(hours, min_periods=1).mean()
    result["previous_1hr_arrivals"] = prior
    capacity = result["current_patients"] + result["available_beds"]
    result["occupancy_percentage"] = (result["current_patients"] / capacity.replace(0, 1) * 100).clip(0, 100)
    result["bed_availability_percentage"] = (result["available_beds"] / capacity.replace(0, 1) * 100).clip(0, 100)
    result["doctor_availability_percentage"] = (result["doctors_available"] / result["doctors_scheduled"].replace(0, 1) * 100).clip(0, 100)
    result["nurse_availability_percentage"] = (result["nurses_available"] / result["nurses_scheduled"].replace(0, 1) * 100).clip(0, 100)
    result["event_indicator"] = ((result["holiday"] == 1) | (result["local_event"] == 1)).astype(int)
    result["rainy_flag"] = (result["rainfall"] >= 2).astype(int)
    result["flu_index_change_24hr"] = result["flu_index"] - result["flu_index"].shift(24)

    result["next_hour_arrivals"] = arrivals.shift(-1)
    result["next_3hr_arrivals"] = arrivals.shift(-1).rolling(3, min_periods=3).sum().shift(-2)
    result["next_6hr_arrivals"] = arrivals.shift(-1).rolling(6, min_periods=6).sum().shift(-5)
    result["next_24hr_arrivals"] = arrivals.shift(-1).rolling(24, min_periods=24).sum().shift(-23)
    future_occupancy = result["occupancy_percentage"].shift(-1)
    future_wait = result["average_waiting_time"].shift(-1)
    future_patients = result["current_patients"].shift(-1)
    critical = (future_occupancy >= 95) | (future_wait >= 150) | (future_patients >= 46)
    high = (future_occupancy >= 85) | (future_wait >= 100) | (future_patients >= 42)
    moderate = (future_occupancy >= 70) | (future_wait >= 60) | (future_patients >= 34)
    result["congestion_level"] = "NORMAL"
    result.loc[moderate, "congestion_level"] = "MODERATE"
    result.loc[high, "congestion_level"] = "HIGH"
    result.loc[critical, "congestion_level"] = "CRITICAL"
    result.loc[future_occupancy.isna(), "congestion_level"] = None
    result["required_beds"] = result["current_patients"] + result["next_hour_arrivals"].fillna(0).astype(int)
    result["required_doctors"] = (result["required_beds"] / 10).round().clip(lower=1).astype(int)
    result["required_nurses"] = (result["required_beds"] / 4).round().clip(lower=2).astype(int)
    return result