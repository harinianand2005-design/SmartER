# SmartER API

Phase 5 exposes authenticated ML inference over the existing Phase 4 artifacts. The API is decision support for synthetic/anonymized operational data; it does not provide medical diagnoses or autonomous clinical decisions.

## Authentication

Obtain a bearer token with `POST /api/v1/auth/login`, then send:

```text
Authorization: Bearer <access_token>
```

All prediction and model-status routes require an authenticated `ADMIN`, `TRIAGE_NURSE`, or `HEALTH_AUTHORITY` user. Backend role checks protect the routes independently of the frontend.

## Prediction request

`POST /api/v1/predictions/forecast`, `/congestion`, `/resources`, and `/run` accept the same validated JSON body:

```json
{
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
  "er_unit_id": "synthetic-er"
}
```

`/forecast` returns 1h, 3h, 6h, and 24h arrival forecasts. `/congestion` returns a class and probabilities. `/resources` returns required beds, doctors, and nurses. `/run` returns all three result groups and persists the generated records.

`/run` also writes one append-only assessment row in the same transaction. It contains the submitted aggregate input, combined model outputs (including forecasts and resource estimates), SmartER Congestion Score/level, timestamp, ER unit, and requesting user ID. `GET /api/v1/predictions/assessments/history?limit=20&offset=0` returns these records newest-first to authenticated operational users.

## Other routes

- `GET /api/v1/predictions/latest`: latest persisted prediction and resource records.
- `GET /api/v1/models/status`: load state, version, evaluation metadata, and safe artifact names for all eight Phase 4 models.
- `GET /docs`: FastAPI OpenAPI documentation.

## Intelligence and operational alerts

All of these routes require a bearer token. They accept only scenario values and persisted model outputs; they do not make clinical decisions.

- `POST /api/v1/intelligence/congestion-score`: returns the 0-100 SmartER Congestion Score, level, classifier confidence, timestamp, component contributions, and readable formula explanation. The score is an operational indicator, not a medical diagnosis.
- `POST /api/v1/intelligence/explain`: accepts `{ "model": "congestion_classifier", "scenario": { ...prediction request... } }`. Supported model values are `congestion_classifier`, `bed_prediction_model`, `doctor_prediction_model`, and `nurse_prediction_model`. Returns the actual prediction and saved global mean absolute SHAP features. Saved artifacts do not include signed local contributions or base values; `base_value` is therefore `null`.
- `POST /api/v1/intelligence/recommendations`: evaluates explicit threshold rules against real model outputs, persists the generated operational recommendations, and persists deduplicated OPEN alerts.
- `GET /api/v1/intelligence/recommendations/latest`: returns recent persisted recommendations.
- `GET /api/v1/alerts` and `GET /api/v1/alerts/latest`: return persisted measurable threshold alerts, including trigger and threshold values.
- `POST /api/v1/alerts/{alert_id}/resolve`: accepts an optional JSON status body and resolves the alert. ADMIN and TRIAGE_NURSE may resolve; HEALTH_AUTHORITY is read-only.

## Historical analytics

- `GET /api/v1/analytics/summary?start=<ISO datetime>&end=<ISO datetime>&er_unit_id=<id>` returns only persisted observed ER metrics, arrival forecasts, congestion predictions, and resource predictions. Access is limited to ADMIN and HEALTH_AUTHORITY. If no records exist, the relevant arrays and counts are empty/zero; the endpoint does not create sample values. Responses are capped at 2,000 rows per record category.

## Operational metric ingestion

- `POST /api/v1/er-metrics` accepts an observed interval matching the existing `ERMetric` schema: `er_unit_id`, timezone-aware `timestamp`, `arrivals`, `departures`, `active_patients`, `waiting_patients`, `occupied_beds`, `available_beds`, `average_wait_minutes`, and `critical_patient_count`.
- Values must be non-negative and within field bounds. Waiting patients, occupied beds, and critical patients cannot exceed active patients. Timestamps are normalized to UTC.
- ADMIN and TRIAGE_NURSE may submit observations; HEALTH_AUTHORITY is read-only. Successful writes return HTTP 201 and the saved record ID.
- Persisted observations appear in `/api/v1/analytics/summary` and the Analytics page. Prediction scenario requests remain separate and are never treated as observed measurements.

The congestion score weights occupancy 30%, next-hour arrivals 20%, bed pressure 20%, waiting time 20%, and staffing pressure 10%, with a documented small classifier-level adjustment. Alert and recommendation thresholds are documented in `docs/intelligence.md`.

Invalid values return structured HTTP 422 validation errors. Missing/corrupt artifacts return HTTP 503 without crashing the backend. Database persistence failures also return HTTP 503.