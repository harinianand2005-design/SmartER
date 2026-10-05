"""Generate EDA figures and data-derived summary values for the EDA notebook."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def run_eda(input_path: str | Path, output_dir: str | Path) -> dict[str, object]:
    data = pd.read_csv(input_path, parse_dates=["timestamp"])
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook")
    data["date"] = data["timestamp"].dt.date
    data["hour"] = data["timestamp"].dt.hour
    data["day_of_week"] = data["timestamp"].dt.dayofweek
    data["month"] = data["timestamp"].dt.month
    data["occupancy_percentage"] = data["current_patients"] / (data["current_patients"] + data["available_beds"]).replace(0, 1) * 100

    def save(name: str) -> None:
        plt.tight_layout()
        plt.savefig(output / f"{name}.png", dpi=150, bbox_inches="tight")
        plt.close()

    plt.figure(figsize=(12, 4)); sns.lineplot(data=data, x="timestamp", y="patient_arrivals", errorbar=None); plt.title("Patient arrivals over time"); save("01_arrivals_over_time")
    plt.figure(figsize=(10, 4)); sns.histplot(data=data, x="hour", weights="patient_arrivals", discrete=True, bins=24); plt.title("Hourly patient arrival distribution"); save("02_hourly_arrivals")
    daily = data.set_index("timestamp")["patient_arrivals"].resample("D").sum().reset_index(); plt.figure(figsize=(12, 4)); sns.lineplot(data=daily, x="timestamp", y="patient_arrivals", errorbar=None); plt.title("Daily patient arrivals"); save("03_daily_arrivals")
    weekly = data.set_index("timestamp")["patient_arrivals"].resample("W").sum().reset_index(); plt.figure(figsize=(12, 4)); sns.lineplot(data=weekly, x="timestamp", y="patient_arrivals"); plt.title("Weekly patient arrivals"); save("04_weekly_arrivals")
    monthly = data.set_index("timestamp")["patient_arrivals"].resample("MS").sum().reset_index(); plt.figure(figsize=(12, 4)); sns.lineplot(data=monthly, x="timestamp", y="patient_arrivals", marker="o"); plt.title("Monthly patient arrivals"); save("05_monthly_arrivals")
    hourly_wait = data.groupby("hour", as_index=False)["average_waiting_time"].mean(); plt.figure(figsize=(10, 4)); sns.lineplot(data=hourly_wait, x="hour", y="average_waiting_time", marker="o"); plt.title("Average waiting time by hour"); save("06_wait_by_hour")
    plt.figure(figsize=(12, 4)); sns.lineplot(data=data, x="timestamp", y="occupancy_percentage", errorbar=None); plt.axhline(85, color="red", linestyle="--", label="85% reference"); plt.legend(); plt.title("ER occupancy trend"); save("07_occupancy_trend")
    plt.figure(figsize=(7, 5)); sns.scatterplot(data=data.sample(min(5000, len(data)), random_state=42), x="occupancy_percentage", y="average_waiting_time", alpha=.35); plt.title("Occupancy vs waiting time"); save("08_occupancy_wait")
    triage = data[[f"triage_{level}" for level in range(1, 6)]].sum().rename_axis("triage_level").reset_index(name="patients"); plt.figure(figsize=(8, 4)); sns.barplot(data=triage, x="triage_level", y="patients"); plt.title("Triage-level distribution"); save("09_triage_distribution")
    weekday = data.assign(period=data["day_of_week"].lt(5).map({True: "Weekday", False: "Weekend"})); plt.figure(figsize=(7, 4)); sns.boxplot(data=weekday, x="period", y="patient_arrivals"); plt.title("Weekday vs weekend arrivals"); save("10_weekday_weekend")
    plt.figure(figsize=(7, 4)); sns.regplot(data=data.sample(min(5000, len(data)), random_state=42), x="rainfall", y="patient_arrivals", scatter_kws={"alpha": .15}, line_kws={"color": "#ef8354"}); plt.title("Rainfall vs patient arrivals"); save("11_weather_arrivals")
    holiday_summary = data.assign(period=data["holiday"].map({0: "Normal day", 1: "Holiday"})); plt.figure(figsize=(7, 4)); sns.boxplot(data=holiday_summary, x="period", y="patient_arrivals"); plt.title("Holiday vs normal-day arrivals"); save("12_holiday_impact")
    event_summary = data.assign(period=data["local_event"].map({0: "No event", 1: "Local event"})); plt.figure(figsize=(7, 4)); sns.boxplot(data=event_summary, x="period", y="patient_arrivals"); plt.title("Local event impact"); save("13_event_impact")
    plt.figure(figsize=(7, 4)); sns.regplot(data=data.sample(min(5000, len(data)), random_state=42), x="flu_index", y="patient_arrivals", scatter_kws={"alpha": .15}, line_kws={"color": "#2680c2"}); plt.title("Flu index vs patient arrivals"); save("14_flu_arrivals")
    numeric = data.select_dtypes(include="number").drop(columns=["date"], errors="ignore"); plt.figure(figsize=(12, 9)); sns.heatmap(numeric.corr(), cmap="vlag", center=0); plt.title("Correlation matrix"); save("15_correlation_matrix")

    summary = {
        "rows": len(data), "date_start": str(data["timestamp"].min()), "date_end": str(data["timestamp"].max()),
        "mean_arrivals_weekday": float(data.loc[data["day_of_week"] < 5, "patient_arrivals"].mean()),
        "mean_arrivals_weekend": float(data.loc[data["day_of_week"] >= 5, "patient_arrivals"].mean()),
        "mean_arrivals_holiday": float(data.loc[data["holiday"] == 1, "patient_arrivals"].mean()),
        "mean_arrivals_normal_day": float(data.loc[data["holiday"] == 0, "patient_arrivals"].mean()),
        "arrival_wait_correlation": float(data["patient_arrivals"].corr(data["average_waiting_time"])),
        "arrival_flu_correlation": float(data["patient_arrivals"].corr(data["flu_index"])),
    }
    (output / "eda_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("dataset/generated/synthetic_er_hourly.csv"))
    parser.add_argument("--output", type=Path, default=Path("ml/notebooks/outputs"))
    arguments = parser.parse_args()
    print(json.dumps(run_eda(arguments.input, arguments.output), indent=2))