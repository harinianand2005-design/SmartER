from pathlib import Path
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import CurrentUser, DatabaseSession, require_roles
from app.core.config import get_settings
from app.models import Alert, Recommendation, UserRole
from app.schemas.intelligence import AlertResponse, CongestionScoreResponse, ExplainModel, ExplainRequest, ExplanationResponse, IntelligenceRequest, RecommendationResponse, ResolveAlertRequest, WhatIfRequest, WhatIfResponse
from app.services.intelligence import congestion_score, operational_alerts, recommendations, shap_explanation
from app.services.ml_service import ModelServiceError, get_model_service

router = APIRouter(prefix="/intelligence", tags=["intelligence"])
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])
ROLES = (UserRole.ADMIN, UserRole.TRIAGE_NURSE, UserRole.HEALTH_AUTHORITY)


def _inputs(payload, service):
    forecast = service.forecast(payload); congestion = service.congestion(payload); resources = service.resources(payload)
    return forecast, congestion, resources


def _error(error: Exception):
    if isinstance(error, ModelServiceError):
        return HTTPException(status_code=503, detail={"code": "model_unavailable", "message": "A required persisted model is unavailable."})
    return HTTPException(status_code=503, detail={"code": "intelligence_unavailable", "message": "The intelligence service is temporarily unavailable."})


def _persist_alerts(db, payload, alert_items):
    existing_rows = db.scalars(select(Alert).where(Alert.er_unit_id == payload.er_unit_id, Alert.status == "OPEN")).all()
    existing_types = {row.alert_type for row in existing_rows}
    for item in alert_items:
        if item["alert_type"] in existing_types:
            continue
        db.add(Alert(er_unit_id=payload.er_unit_id, alert_type=item["alert_type"], severity=item["severity"], message=json.dumps(jsonable_encoder(item)), status="OPEN"))


def _scenario_intelligence(payload):
    forecast_result, congestion_result, resource_result = _inputs(payload, get_model_service())
    score_result = congestion_score(payload, forecast_result, congestion_result, resource_result)
    alerts_result = operational_alerts(score_result, forecast_result, resource_result, payload)
    return forecast_result, congestion_result, resource_result, score_result, alerts_result


@router.post("/congestion-score", response_model=CongestionScoreResponse, dependencies=[Depends(require_roles(*ROLES))])
def score(payload: IntelligenceRequest, db: DatabaseSession, _: CurrentUser):
    try:
        _, _, _, score_result, alert_items = _scenario_intelligence(payload)
        _persist_alerts(db, payload, alert_items)
        db.commit()
        return score_result
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail={"code": "database_unavailable", "message": "Operational alerts could not be persisted"}) from error
    except Exception as error:
        raise _error(error) from error


@router.post("/recommendations", response_model=list[RecommendationResponse], dependencies=[Depends(require_roles(*ROLES))])
def create_recommendations(payload: IntelligenceRequest, db: DatabaseSession, _: CurrentUser):
    try:
        forecast, congestion, resources, score_result, alert_items = _scenario_intelligence(payload); items = recommendations(score_result, forecast, resources, payload)
        for item in items:
            db.add(Recommendation(er_unit_id=payload.er_unit_id, priority=item["priority"], category="OPERATIONS", title=item["title"], description=json.dumps(jsonable_encoder({"reason": item["reason"], "supporting_metric": item["supporting_metric"], "timestamp": item["timestamp"]})), status="OPEN"))
        _persist_alerts(db, payload, alert_items)
        db.commit(); return items
    except SQLAlchemyError as error:
        db.rollback(); raise HTTPException(status_code=503, detail={"code": "database_unavailable", "message": "Recommendations could not be persisted"}) from error
    except Exception as error:
        raise _error(error) from error


@router.get("/recommendations/latest", response_model=list[RecommendationResponse], dependencies=[Depends(require_roles(*ROLES))])
def latest_recommendations(db: DatabaseSession, _: CurrentUser):
    rows = db.scalars(select(Recommendation).order_by(desc(Recommendation.created_at)).limit(25)).all()
    results = []
    for row in rows:
        try:
            details = json.loads(row.description)
        except (TypeError, ValueError):
            details = {"reason": row.description, "supporting_metric": "Not recorded"}
        results.append(RecommendationResponse(id=row.id, priority=row.priority, title=row.title, reason=details.get("reason", row.description), supporting_metric=details.get("supporting_metric", "Not recorded"), timestamp=row.created_at, status=row.status))
    return results


@router.post("/explain", response_model=ExplanationResponse, dependencies=[Depends(require_roles(*ROLES))])
def explain(payload: ExplainRequest, _: CurrentUser):
    try:
        service = get_model_service()
        key_by_model = {ExplainModel.CONGESTION: "congestion", ExplainModel.BEDS: "beds", ExplainModel.DOCTORS: "doctors", ExplainModel.NURSES: "nurses"}
        key = key_by_model[payload.model]
        loaded, features, raw_prediction = service._predict(key, payload.scenario)
        artifact = loaded["artifact"]
        if payload.model == ExplainModel.CONGESTION:
            prediction = str(artifact["label_encoder"].inverse_transform([int(raw_prediction)])[0])
        else:
            prediction = float(raw_prediction)
        feature_values = {name: float(value) for name, value in features.iloc[0].items()}
        explainability_dir = Path(get_settings().ml_explainability_dir)
        if not explainability_dir.is_absolute():
            explainability_dir = Path(__file__).resolve().parents[5] / explainability_dir
        return shap_explanation(payload.model.value, prediction, loaded["metadata"].get("version", "unknown"), explainability_dir, feature_values)
    except Exception as error:
        raise _error(error) from error


def _alert_response(row: Alert) -> AlertResponse:
    try:
        details = json.loads(row.message)
    except (TypeError, ValueError):
        details = {"title": row.alert_type.replace("_", " ").title(), "description": row.message}
    return AlertResponse(id=row.id, alert_type=row.alert_type, severity=row.severity, title=details.get("title", row.alert_type.replace("_", " ").title()), description=details.get("description", row.message), trigger_value=details.get("trigger_value"), threshold=details.get("threshold"), timestamp=row.created_at, status=row.status)


@alerts_router.get("", response_model=list[AlertResponse], dependencies=[Depends(require_roles(*ROLES))])
def alerts(db: DatabaseSession, _: CurrentUser):
    return [_alert_response(row) for row in db.scalars(select(Alert).order_by(desc(Alert.created_at)).limit(50)).all()]


@alerts_router.get("/latest", response_model=list[AlertResponse], dependencies=[Depends(require_roles(*ROLES))])
def latest_alerts(db: DatabaseSession, _: CurrentUser):
    return alerts(db, _)


@alerts_router.post("/{alert_id}/resolve", response_model=AlertResponse, dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.TRIAGE_NURSE))])
def resolve_alert(alert_id: int, payload: ResolveAlertRequest, db: DatabaseSession, _: CurrentUser):
    row = db.get(Alert, alert_id)
    if row is None: raise HTTPException(status_code=404, detail={"code": "alert_not_found", "message": "Alert not found"})
    try:
        row.status = "RESOLVED"; db.commit(); db.refresh(row); return _alert_response(row)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail={"code": "database_unavailable", "message": "The alert could not be resolved"}) from error

@router.post("/what-if", response_model=WhatIfResponse, dependencies=[Depends(require_roles(*ROLES))])

def what_if(
    payload: WhatIfRequest,
    _: CurrentUser,
) -> WhatIfResponse:
    if payload.expected_arrival_change > 0:
        pressure = "Higher demand pressure"
    elif payload.expected_arrival_change < 0:
        pressure = "Lower demand pressure"
    else:
        pressure = "No demand adjustment"

    return WhatIfResponse(
        demand_pressure=pressure,
        additional_beds=payload.additional_beds,
        additional_doctors=payload.additional_doctors,
        additional_nurses=payload.additional_nurses,
        expected_arrival_change=payload.expected_arrival_change,
    )