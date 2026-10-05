from datetime import datetime, timezone


PAYLOAD = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
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
    "er_unit_id": "test-er",
}


def token_for(client, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_model_status_loads_all_artifacts(client, users):
    token = token_for(client, "admin@example.com", "AdminPass123!")
    response = client.get("/api/v1/models/status", headers=headers(token))
    assert response.status_code == 200
    assert len(response.json()["models"]) == 8
    assert all(model["loaded"] for model in response.json()["models"])


def test_prediction_endpoints_return_valid_outputs_and_persist(client, users):
    token = token_for(client, "nurse@example.com", "NursePass123!")
    auth = headers(token)
    forecast = client.post("/api/v1/predictions/forecast", json=PAYLOAD, headers=auth)
    congestion = client.post("/api/v1/predictions/congestion", json=PAYLOAD, headers=auth)
    resources = client.post("/api/v1/predictions/resources", json=PAYLOAD, headers=auth)
    combined = client.post("/api/v1/predictions/run", json=PAYLOAD, headers=auth)
    assert forecast.status_code == congestion.status_code == resources.status_code == combined.status_code == 200
    assert set(forecast.json()["forecasts"]) == {"1h", "3h", "6h", "24h"}
    assert congestion.json()["congestion_level"] in {"NORMAL", "MODERATE", "HIGH", "CRITICAL"}
    assert all(value >= 0 for value in resources.json().values() if isinstance(value, (int, float)))
    latest = client.get("/api/v1/predictions/latest", headers=auth)
    assert latest.status_code == 200
    assert latest.json()["forecasts"]
    assert latest.json()["resources"]


def test_combined_prediction_is_saved_with_input_score_and_outputs(client, users):
    token = token_for(client, "admin@example.com", "AdminPass123!")
    auth = headers(token)
    run_response = client.post("/api/v1/predictions/run", json=PAYLOAD, headers=auth)
    assert run_response.status_code == 200
    run_body = run_response.json()
    assert 0 <= run_body["congestion_score"]["score"] <= 100
    newer_payload = {**PAYLOAD, "timestamp": "2026-09-07T13:00:00Z"}
    newer_response = client.post("/api/v1/predictions/run", json=newer_payload, headers=auth)
    assert newer_response.status_code == 200

    history_response = client.get("/api/v1/predictions/assessments/history", headers=auth)
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["count"] == 2
    assessment = history["assessments"][0]
    assert assessment["input_payload"]["timestamp"] == newer_payload["timestamp"]
    assert assessment["input_payload"]["patient_arrivals"] == newer_payload["patient_arrivals"]
    assert assessment["prediction_payload"]["forecast"]["forecasts"] == newer_response.json()["forecast"]["forecasts"]
    assert assessment["prediction_payload"]["resources"] == newer_response.json()["resources"]
    assert assessment["congestion_score"] == newer_response.json()["congestion_score"]["score"]


def test_assessment_history_requires_authentication(client):
    assert client.get("/api/v1/predictions/assessments/history").status_code == 401


def test_prediction_validation_and_authentication(client, users):
    invalid = {**PAYLOAD, "average_waiting_time": -1}
    assert client.post("/api/v1/predictions/forecast", json=invalid).status_code == 401
    token = token_for(client, "nurse@example.com", "NursePass123!")
    response = client.post("/api/v1/predictions/forecast", json=invalid, headers=headers(token))
    assert response.status_code == 422
    missing = dict(PAYLOAD)
    del missing["triage_1"]
    assert client.post("/api/v1/predictions/forecast", json=missing, headers=headers(token)).status_code == 422


def test_role_authorization_for_predictions(client, users):
    authority = token_for(client, "authority@example.com", "AuthorityPass123!")
    response = client.post("/api/v1/predictions/run", json=PAYLOAD, headers=headers(authority))
    assert response.status_code == 200