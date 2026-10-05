from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models import ERMetric


METRIC = {
    "er_unit_id": "ingestion-test-unit",
    "timestamp": datetime(2026, 9, 7, 12, tzinfo=timezone.utc).isoformat(),
    "arrivals": 9,
    "departures": 4,
    "active_patients": 25,
    "waiting_patients": 7,
    "occupied_beds": 20,
    "available_beds": 10,
    "average_wait_minutes": 47.5,
    "critical_patient_count": 2,
}


def auth(client, email: str, password: str) -> dict[str, str]:
    result = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert result.status_code == 200
    return {"Authorization": f"Bearer {result.json()['access_token']}"}


def test_metric_ingest_persists_and_analytics_returns_same_record(client, users):
    headers = auth(client, "nurse@example.com", "NursePass123!")
    response = client.post("/api/v1/er-metrics", json=METRIC, headers=headers)
    assert response.status_code == 201
    saved = response.json()
    assert saved["id"] > 0
    assert saved["arrivals"] == METRIC["arrivals"]
    assert saved["average_wait_minutes"] == METRIC["average_wait_minutes"]

    with SessionLocal() as db:
        persisted = db.get(ERMetric, saved["id"])
        assert persisted is not None
        assert persisted.er_unit_id == METRIC["er_unit_id"]

    admin_headers = auth(client, "admin@example.com", "AdminPass123!")
    analytics = client.get("/api/v1/analytics/summary?er_unit_id=ingestion-test-unit", headers=admin_headers)
    assert analytics.status_code == 200
    observations = analytics.json()["observed_metrics"]
    assert len(observations) == 1
    assert observations[0]["arrivals"] == saved["arrivals"]
    assert observations[0]["active_patients"] == saved["active_patients"]
    assert observations[0]["average_wait_minutes"] == saved["average_wait_minutes"]


def test_metric_ingest_requires_auth_and_write_role(client, users):
    assert client.post("/api/v1/er-metrics", json=METRIC).status_code == 401
    authority_headers = auth(client, "authority@example.com", "AuthorityPass123!")
    assert client.post("/api/v1/er-metrics", json=METRIC, headers=authority_headers).status_code == 403
    with SessionLocal() as db:
        assert db.query(ERMetric).count() == 0


def test_metric_ingest_rejects_invalid_values_and_missing_fields(client, users):
    headers = auth(client, "admin@example.com", "AdminPass123!")
    negative = {**METRIC, "arrivals": -1}
    assert client.post("/api/v1/er-metrics", json=negative, headers=headers).status_code == 422
    inconsistent = {**METRIC, "waiting_patients": 26}
    assert client.post("/api/v1/er-metrics", json=inconsistent, headers=headers).status_code == 422
    naive_timestamp = {**METRIC, "timestamp": "2026-09-07T12:00:00"}
    assert client.post("/api/v1/er-metrics", json=naive_timestamp, headers=headers).status_code == 422
    missing = dict(METRIC)
    del missing["arrivals"]
    assert client.post("/api/v1/er-metrics", json=missing, headers=headers).status_code == 422