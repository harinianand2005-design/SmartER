from datetime import datetime, timezone

import pytest

from app.models import Alert, Recommendation
from app.services.intelligence import level_for_score, operational_alerts, recommendations


PAYLOAD = {
    "timestamp": datetime(2026, 9, 7, 12, tzinfo=timezone.utc).isoformat(),
    "patient_arrivals": 12, "current_patients": 30, "available_beds": 18,
    "doctors_available": 6, "nurses_available": 14, "doctors_scheduled": 8,
    "nurses_scheduled": 18, "average_waiting_time": 55,
    "triage_1": 1, "triage_2": 2, "triage_3": 4, "triage_4": 3, "triage_5": 2,
    "temperature": 12, "rainfall": 1.5, "holiday": 0, "local_event": 0, "flu_index": 40,
    "weather_category": "clear", "er_unit_id": "intelligence-test-er",
}


@pytest.mark.parametrize("value, expected", [(30, "LOW"), (31, "MODERATE"), (60, "MODERATE"), (61, "HIGH"), (80, "HIGH"), (81, "CRITICAL")])
def test_congestion_score_level_boundaries(value, expected):
    assert level_for_score(value).value == expected


def test_recommendation_and_alert_rules_use_supplied_metrics():
    from app.schemas.predictions import ERPredictionInput

    payload = ERPredictionInput(**PAYLOAD)
    score = {"score": 85.0, "level": level_for_score(85), "timestamp": payload.timestamp}
    forecast = {"forecasts": {"1h": 20.0}}
    resources = {"required_beds": 24.0, "required_doctors": 10.0, "required_nurses": 22.0}
    items = recommendations(score, forecast, resources, payload)
    alert_items = operational_alerts(score, forecast, resources, payload)
    assert {"Review bed allocation", "Review upcoming staffing coverage", "Review nursing coverage", "Increase monitoring frequency"}.issubset({item["title"] for item in items})
    assert {"CRITICAL_CONGESTION", "BED_SHORTAGE", "DOCTOR_SHORTAGE", "NURSE_SHORTAGE", "ARRIVAL_SPIKE"}.issubset({item["alert_type"] for item in alert_items})


def token_for(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_intelligence_endpoints_persist_and_explain(client, users):
    auth = {"Authorization": f"Bearer {token_for(client, 'admin@example.com', 'AdminPass123!')}"}
    score = client.post("/api/v1/intelligence/congestion-score", json=PAYLOAD, headers=auth)
    assert score.status_code == 200
    assert 0 <= score.json()["score"] <= 100
    assert score.json()["level"] in {"LOW", "MODERATE", "HIGH", "CRITICAL"}
    assert score.json()["factors"]

    explain = client.post("/api/v1/intelligence/explain", json={"model": "congestion_classifier", "scenario": PAYLOAD}, headers=auth)
    assert explain.status_code == 200
    assert "not medical causation" in explain.json()["interpretation"].lower()
    assert explain.json()["top_contributing_features"]

    created = client.post("/api/v1/intelligence/recommendations", json=PAYLOAD, headers=auth)
    assert created.status_code == 200
    latest_recommendations = client.get("/api/v1/intelligence/recommendations/latest", headers=auth)
    latest_alerts = client.get("/api/v1/alerts/latest", headers=auth)
    assert latest_recommendations.status_code == latest_alerts.status_code == 200
    assert latest_recommendations.json()[0]["supporting_metric"] != "Not recorded"
    assert client.get("/api/v1/alerts", headers=auth).status_code == 200


def test_intelligence_auth_and_alert_resolution_permissions(client, users):
    assert client.post("/api/v1/intelligence/congestion-score", json=PAYLOAD).status_code == 401
    triage = {"Authorization": f"Bearer {token_for(client, 'nurse@example.com', 'NursePass123!')}"}
    alert_payload = {**PAYLOAD, "average_waiting_time": 150, "available_beds": 0}
    score = client.post("/api/v1/intelligence/congestion-score", json=alert_payload, headers=triage)
    assert score.status_code == 200
    created_recommendations = client.post("/api/v1/intelligence/recommendations", json=alert_payload, headers=triage)
    assert created_recommendations.status_code == 200
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        alert = db.query(Alert).first()
        recommendation = db.query(Recommendation).first()
        assert recommendation is not None
        alert_id = alert.id if alert else None
    assert alert_id is not None
    authority = {"Authorization": f"Bearer {token_for(client, 'authority@example.com', 'AuthorityPass123!')}"}
    assert client.post(f"/api/v1/alerts/{alert_id}/resolve", json={}, headers=authority).status_code == 403
    assert client.post(f"/api/v1/alerts/{alert_id}/resolve", json={}, headers=triage).status_code == 200