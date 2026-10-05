"""Transparent congestion scoring, SHAP summaries, recommendations, and alerts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.intelligence import CongestionLevel, ScoreFactor
from app.services.ml_service import ModelService


def _bounded(value: float) -> float:
    return max(0.0, min(100.0, value))


def level_for_score(score: float) -> CongestionLevel:
    if score <= 30:
        return CongestionLevel.LOW
    if score <= 60:
        return CongestionLevel.MODERATE
    if score <= 80:
        return CongestionLevel.HIGH
    return CongestionLevel.CRITICAL


def congestion_score(payload, forecast: dict, congestion: dict, resources: dict) -> dict:
    """Calculate a weighted 0-100 operational signal; not a medical diagnosis."""
    capacity = max(1, payload.current_patients + payload.available_beds)
    factors = [
        ScoreFactor(name="ER occupancy", value=payload.current_patients / capacity * 100, contribution=0, explanation="Current patients divided by observed capacity."),
        ScoreFactor(name="Predicted arrivals", value=forecast["forecasts"]["1h"], contribution=0, explanation="Model-predicted arrivals during the next hour."),
        ScoreFactor(name="Bed pressure", value=max(0, resources["required_beds"] - payload.available_beds), contribution=0, explanation="Predicted bed requirement above available beds."),
        ScoreFactor(name="Waiting time", value=payload.average_waiting_time, contribution=0, explanation="Current average waiting time in minutes."),
        ScoreFactor(name="Staff availability", value=(payload.doctors_available / max(1, payload.doctors_scheduled) + payload.nurses_available / max(1, payload.nurses_scheduled)) * 50, contribution=0, explanation="Combined doctor and nurse availability percentage."),
    ]
    raw_values = [
        factors[0].value,
        _bounded(factors[1].value / 20 * 100),
        _bounded(factors[2].value / max(1, payload.available_beds) * 100),
        _bounded(factors[3].value / 120 * 100),
        _bounded(100 - factors[4].value),
    ]
    weights = [0.30, 0.20, 0.20, 0.20, 0.10]
    for factor, raw, weight in zip(factors, raw_values, weights):
        factor.contribution = round(raw * weight, 2)
    score = round(_bounded(sum(factor.contribution for factor in factors) + (10 if congestion["congestion_level"] == "CRITICAL" else 5 if congestion["congestion_level"] == "HIGH" else 0)), 2)
    level = level_for_score(score)
    return {"score": score, "level": level, "confidence": congestion.get("confidence"), "timestamp": payload.timestamp, "factors": [factor.model_dump() for factor in factors], "explanation": "Weighted operational signal: occupancy 30%, arrivals 20%, bed pressure 20%, waiting time 20%, staffing pressure 10%, with a small classifier-level adjustment."}


def recommendations(score: dict, forecast: dict, resources: dict, payload) -> list[dict]:
    now = payload.timestamp
    items = []
    def add(priority, title, reason, metric):
        items.append({"priority": priority, "title": title, "reason": reason, "supporting_metric": metric, "timestamp": now, "status": "OPEN"})
    if score["level"] in {CongestionLevel.HIGH, CongestionLevel.CRITICAL}: add("HIGH" if score["level"] == CongestionLevel.HIGH else "CRITICAL", "Increase monitoring frequency", "Congestion is at an elevated operational level.", f"Score {score['score']}/100")
    if resources["required_beds"] > payload.available_beds: add("HIGH", "Review bed allocation", "Predicted bed requirement exceeds current available beds.", f"Required {resources['required_beds']:.1f} vs available {payload.available_beds}")
    if resources["required_doctors"] > payload.doctors_available: add("HIGH", "Review upcoming staffing coverage", "Predicted doctor requirement exceeds available doctors.", f"Required {resources['required_doctors']:.1f} vs available {payload.doctors_available}")
    if resources["required_nurses"] > payload.nurses_available: add("HIGH", "Review nursing coverage", "Predicted nurse requirement exceeds available nurses.", f"Required {resources['required_nurses']:.1f} vs available {payload.nurses_available}")
    if forecast["forecasts"]["1h"] > max(1, payload.available_beds): add("MODERATE", "Prepare additional operational capacity", "Predicted arrivals may exceed immediately available bed capacity.", f"Next-hour arrivals {forecast['forecasts']['1h']:.1f}")
    if not items: add("LOW", "Continue routine monitoring", "No configured operational thresholds are currently exceeded.", f"Score {score['score']}/100")
    return items


def operational_alerts(score: dict, forecast: dict, resources: dict, payload) -> list[dict]:
    timestamp = payload.timestamp
    alerts = []

    def add(alert_type: str, severity: str, description: str, trigger: float, threshold: float) -> None:
        alerts.append({"alert_type": alert_type, "severity": severity, "title": alert_type.replace("_", " ").title(), "description": description, "trigger_value": float(trigger), "threshold": float(threshold), "timestamp": timestamp, "status": "OPEN"})

    if score["score"] >= 81:
        add("CRITICAL_CONGESTION", "CRITICAL", "SmartER Congestion Score reached the critical threshold.", score["score"], 81)
    elif score["score"] >= 61:
        add("HIGH_CONGESTION", "HIGH", "SmartER Congestion Score reached the high threshold.", score["score"], 61)
    if resources["required_beds"] > payload.available_beds:
        add("BED_SHORTAGE", "HIGH", "Predicted bed requirement exceeds available beds.", resources["required_beds"], payload.available_beds)
    if resources["required_doctors"] > payload.doctors_available:
        add("DOCTOR_SHORTAGE", "HIGH", "Predicted doctor requirement exceeds available doctors.", resources["required_doctors"], payload.doctors_available)
    if resources["required_nurses"] > payload.nurses_available:
        add("NURSE_SHORTAGE", "HIGH", "Predicted nurse requirement exceeds available nurses.", resources["required_nurses"], payload.nurses_available)
    next_hour = forecast["forecasts"]["1h"]
    spike_threshold = max(payload.patient_arrivals + 5, payload.patient_arrivals * 1.5)
    if next_hour > spike_threshold:
        add("ARRIVAL_SPIKE", "MODERATE", "Next-hour arrival forecast exceeds the scenario arrival baseline threshold.", next_hour, spike_threshold)
    if payload.average_waiting_time >= 120:
        add("WAITING_TIME_INCREASE", "HIGH", "Average waiting time reached the configured operational threshold.", payload.average_waiting_time, 120)
    return alerts


def shap_explanation(model_name: str, prediction: str | float, version: str, output_root: Path, feature_values: dict[str, float] | None = None) -> dict:
    summary_path = output_root / f"{model_name}_shap.json"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        features = summary.get("features", [])[:8]
        if feature_values is not None:
            features = [{**item, "feature_value": feature_values.get(item["feature"])} for item in features]
    except (OSError, ValueError):
        features = []
    return {"model_name": model_name, "model_version": version, "prediction": prediction, "base_value": None, "top_contributing_features": features, "timestamp": datetime.now(timezone.utc), "interpretation": "Features contributing to the model prediction. Values shown are global mean absolute SHAP importance, not signed scenario-level contributions and not medical causation."}