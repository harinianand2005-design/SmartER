from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models import ERMetric, Prediction, ResourcePrediction


def get_token(client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_analytics_returns_empty_without_persisted_history(client, users):
    headers = {"Authorization": f"Bearer {get_token(client, 'authority@example.com', 'AuthorityPass123!')}"}
    response = client.get("/api/v1/analytics/summary", headers=headers)
    assert response.status_code == 200
    assert response.json()["summary"]["observed_metric_count"] == 0
    assert response.json()["observed_metrics"] == []
    assert response.json()["arrival_forecasts"] == []


def test_analytics_reads_persisted_values_and_filters(client, users):
    timestamp = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)
    with SessionLocal() as db:
        db.add(ERMetric(er_unit_id="unit-a", timestamp=timestamp, arrivals=7, departures=3, active_patients=20, waiting_patients=5, occupied_beds=20, available_beds=10, average_wait_minutes=42, critical_patient_count=1))
        db.add(Prediction(er_unit_id="unit-a", prediction_type="arrival_forecast_1h", target_timestamp=timestamp, predicted_value=9.5, model_version="1.0.0"))
        db.add(Prediction(er_unit_id="unit-a", prediction_type="congestion", target_timestamp=timestamp, predicted_value=0.8, confidence=0.8, congestion_level="HIGH", model_version="1.0.0"))
        db.add(ResourcePrediction(er_unit_id="unit-a", target_timestamp=timestamp, required_beds=24, required_doctors=3, required_nurses=6, model_version="1.0.0"))
        db.commit()

    headers = {"Authorization": f"Bearer {get_token(client, 'admin@example.com', 'AdminPass123!')}"}
    response = client.get("/api/v1/analytics/summary?er_unit_id=unit-a&start=2026-09-07T00:00:00Z&end=2026-09-08T00:00:00Z", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["observed_metric_count"] == 1
    assert body["observed_metrics"][0]["arrivals"] == 7
    assert body["observed_metrics"][0]["occupancy_percentage"] == 20 / 30 * 100
    assert body["arrival_forecasts"][0]["predicted_arrivals"] == 9.5
    assert body["congestion_history"][0]["congestion_level"] == "HIGH"
    assert body["resource_history"][0]["required_beds"] == 24


def test_analytics_role_protection_and_invalid_date_range(client, users):
    nurse_headers = {"Authorization": f"Bearer {get_token(client, 'nurse@example.com', 'NursePass123!')}"}
    assert client.get("/api/v1/analytics/summary", headers=nurse_headers).status_code == 403
    admin_headers = {"Authorization": f"Bearer {get_token(client, 'admin@example.com', 'AdminPass123!')}"}
    response = client.get("/api/v1/analytics/summary?start=2026-09-08T00:00:00Z&end=2026-09-07T00:00:00Z", headers=admin_headers)
    assert response.status_code == 422


def test_real_prediction_run_persists_outputs_visible_in_analytics(client, users):
    token = get_token(client, "admin@example.com", "AdminPass123!")
    headers = {"Authorization": f"Bearer {token}"}
    scenario = {
        "timestamp": "2026-09-07T12:00:00Z",
        "patient_arrivals": 12,
        "current_patients": 30,
        "available_beds": 18,
        "doctors_available": 6,
        "nurses_available": 14,
        "doctors_scheduled": 8,
        "nurses_scheduled": 18,
        "average_waiting_time": 55,
        "triage_1": 1,
        "triage_2": 2,
        "triage_3": 4,
        "triage_4": 3,
        "triage_5": 2,
        "temperature": 12,
        "rainfall": 1.5,
        "holiday": 0,
        "local_event": 0,
        "flu_index": 40,
        "weather_category": "clear",
        "er_unit_id": "workflow-test-unit",
    }
    prediction = client.post("/api/v1/predictions/run", json=scenario, headers=headers)
    assert prediction.status_code == 200
    assert set(prediction.json()["forecast"]["forecasts"]) == {"1h", "3h", "6h", "24h"}

    analytics = client.get("/api/v1/analytics/summary?er_unit_id=workflow-test-unit", headers=headers)
    assert analytics.status_code == 200
    body = analytics.json()
    assert body["summary"]["observed_metric_count"] == 0
    assert body["summary"]["forecast_count"] == 4
    assert body["summary"]["congestion_prediction_count"] == 1
    assert body["summary"]["resource_prediction_count"] == 1
    assert body["arrival_forecasts"]
    assert body["resource_history"][0]["required_beds"] == round(prediction.json()["resources"]["required_beds"])