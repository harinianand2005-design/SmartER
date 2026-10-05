"""Generate reproducible synthetic hourly emergency-room operations data."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_COLUMNS = [
    "timestamp", "patient_arrivals", "current_patients", "available_beds",
    "doctors_available", "nurses_available", "average_waiting_time",
    "triage_1", "triage_2", "triage_3", "triage_4", "triage_5",
    "temperature", "rainfall", "holiday", "local_event", "flu_index",
    "weather_category", "doctors_scheduled", "nurses_scheduled",
]


def _holiday_dates(timestamps: pd.DatetimeIndex) -> np.ndarray:
    fixed_dates = {(1, 1), (7, 1), (12, 25), (12, 31)}
    return np.array([(date.month, date.day) in fixed_dates for date in timestamps], dtype=bool)


def generate_dataset(
    periods: int = 3 * 365 * 24,
    start: str = "2022-01-01",
    seed: int = 42,
    total_beds: int = 48,
) -> pd.DataFrame:
    """Create an hourly synthetic ER dataset with no personal information."""
    if periods < 48:
        raise ValueError("periods must cover at least two days")
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range(start=start, periods=periods, freq="h", tz="UTC")
    hour = timestamps.hour.to_numpy()
    day_of_week = timestamps.dayofweek.to_numpy()
    day_of_year = timestamps.dayofyear.to_numpy()
    weekend = day_of_week >= 5
    holiday = _holiday_dates(timestamps)

    evening_peak = 4.0 * np.exp(-((hour - 18) ** 2) / 18)
    morning_peak = 2.4 * np.exp(-((hour - 9) ** 2) / 14)
    overnight_dip = -1.8 * np.exp(-((hour - 3) ** 2) / 10)
    weekend_effect = np.where(weekend, -1.0, 0.8)
    seasonal_effect = 1.5 * np.sin(2 * np.pi * (day_of_year - 30) / 365)
    flu_index = np.clip(35 + 28 * np.sin(2 * np.pi * (day_of_year - 25) / 365) + rng.normal(0, 4, periods), 5, 100)
    flu_effect = (flu_index - 35) / 24
    rainfall = rng.gamma(shape=1.3, scale=1.2, size=periods) * (1.2 + 0.5 * np.sin(2 * np.pi * day_of_year / 365))
    rainfall = np.round(np.clip(rainfall, 0, 18), 2)
    temperature = 12 + 11 * np.sin(2 * np.pi * (day_of_year - 80) / 365) + rng.normal(0, 2.2, periods)
    local_event = (rng.random(periods) < np.where((hour >= 17) & (hour <= 22), 0.035, 0.008)).astype(int)
    event_effect = local_event * rng.integers(4, 11, periods)
    holiday_effect = holiday.astype(int) * -1.8

    arrival_rate = np.clip(8.5 + evening_peak + morning_peak + overnight_dip + weekend_effect + seasonal_effect + flu_effect + holiday_effect + event_effect, 0.8, None)
    spike = rng.random(periods) < 0.006
    arrival_rate = arrival_rate * np.where(spike, rng.uniform(1.8, 3.3, periods), 1.0)
    arrivals = rng.poisson(arrival_rate).astype(int)

    scheduled_doctors = np.where((hour >= 8) & (hour < 20), 8, 5)
    scheduled_nurses = np.where((hour >= 8) & (hour < 20), 18, 12)
    doctors_available = np.maximum(scheduled_doctors - rng.binomial(scheduled_doctors, 0.08), 1)
    nurses_available = np.maximum(scheduled_nurses - rng.binomial(scheduled_nurses, 0.08), 2)

    current_patients = np.zeros(periods, dtype=int)
    departures = np.zeros(periods, dtype=int)
    for index in range(periods):
        prior = current_patients[index - 1] if index else 18
        discharge_rate = min(prior, max(1, int(round(prior * 0.28 + rng.normal(0, 1)))))
        departures[index] = discharge_rate
        current_patients[index] = min(total_beds, max(0, prior + arrivals[index] - discharge_rate))
    occupied_beds = np.minimum(current_patients, total_beds)
    available_beds = np.maximum(total_beds - occupied_beds, 0)
    occupancy = occupied_beds / total_beds
    waiting_time = np.clip(18 + occupancy * 105 + arrivals * 1.4 - nurses_available * 0.7 + rng.normal(0, 6, periods), 2, 240)

    triage_probabilities = np.array([0.04, 0.16, 0.34, 0.31, 0.15])
    triage = np.array([rng.multinomial(int(count), triage_probabilities) for count in arrivals])
    weather_category = np.select([rainfall >= 8, rainfall >= 2], ["storm", "rain"], default="clear")
    return pd.DataFrame({
        "timestamp": timestamps, "patient_arrivals": arrivals, "current_patients": current_patients,
        "available_beds": available_beds, "doctors_available": doctors_available,
        "nurses_available": nurses_available, "average_waiting_time": np.round(waiting_time, 2),
        "triage_1": triage[:, 0], "triage_2": triage[:, 1], "triage_3": triage[:, 2],
        "triage_4": triage[:, 3], "triage_5": triage[:, 4], "temperature": np.round(temperature, 2),
        "rainfall": rainfall, "holiday": holiday.astype(int), "local_event": local_event,
        "flu_index": np.round(flu_index, 2), "weather_category": weather_category,
        "doctors_scheduled": scheduled_doctors, "nurses_scheduled": scheduled_nurses,
    }, columns=DEFAULT_COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic SmartER ER data")
    parser.add_argument("--periods", type=int, default=3 * 365 * 24)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("dataset/generated/synthetic_er_hourly.csv"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate_dataset(periods=args.periods, seed=args.seed).to_csv(args.output, index=False)
    print(f"Generated {args.periods:,} hourly rows at {args.output}")


if __name__ == "__main__":
    main()