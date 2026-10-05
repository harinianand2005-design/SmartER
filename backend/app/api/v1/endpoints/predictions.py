
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import CurrentUser, DatabaseSession, require_roles
from app.models import AIAssessment, Prediction, ResourcePrediction, UserRole
from app.schemas.predictions import (
    AIAssessmentHistoryItem,
    AIAssessmentHistoryResponse,
    CombinedPredictionResponse,
    CongestionResponse,
    ERPredictionInput,
    ForecastResponse,
    LatestPredictionResponse,
    ModelStatusResponse,
    ResourceResponse,
)
from app.services.ml_service import ModelServiceError, get_model_service
from app.services.intelligence import congestion_score as calculate_congestion_score


router = APIRouter(prefix="/predictions", tags=["predictions"])
models_router = APIRouter(prefix="/models", tags=["models"])

OPERATIONAL_ROLES = (
    UserRole.ADMIN,
    UserRole.TRIAGE_NURSE,
    UserRole.HEALTH_AUTHORITY,
)


def _service():
    return get_model_service()


def _prediction_error(error: Exception) -> HTTPException:
    if isinstance(error, ModelServiceError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "model_unavailable",
                "message": str(error),
            },
        )

    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "prediction_failed",
            "message": "Prediction service is temporarily unavailable",
        },
    )


def _persist_forecast(
    db,
    payload: ERPredictionInput,
    result: dict,
) -> None:
    for horizon, value in result["forecasts"].items():
        hours = int(horizon.removesuffix("h"))
        db.add(
            Prediction(
                er_unit_id=payload.er_unit_id,
                prediction_type=f"arrival_forecast_{horizon}",
                target_timestamp=payload.timestamp + timedelta(hours=hours),
                predicted_value=value,
                model_version=result["model_version"],
            )
        )


def _persist_resources(
    db,
    payload: ERPredictionInput,
    result: dict,
) -> None:
    db.add(
        ResourcePrediction(
            er_unit_id=payload.er_unit_id,
            target_timestamp=payload.timestamp,
            required_beds=round(result["required_beds"]),
            required_doctors=round(result["required_doctors"]),
            required_nurses=round(result["required_nurses"]),
            model_version=",".join(
                sorted(set(result["model_versions"].values()))
            ),
        )
    )


def _persist_congestion(
    db,
    payload: ERPredictionInput,
    result: dict,
) -> None:
    db.add(
        Prediction(
            er_unit_id=payload.er_unit_id,
            prediction_type="congestion",
            target_timestamp=payload.timestamp,
            predicted_value=result["confidence"],
            confidence=result["confidence"],
            congestion_level=result["congestion_level"],
            model_version=result["model_version"],
        )
    )


def _commit(db) -> None:
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail={
                "code": "database_unavailable",
                "message": "Prediction could not be persisted",
            },
        ) from error


@router.post(
    "/forecast",
    response_model=ForecastResponse,
    dependencies=[Depends(require_roles(*OPERATIONAL_ROLES))],
)
def forecast(
    payload: ERPredictionInput,
    db: DatabaseSession,
    _: CurrentUser,
) -> ForecastResponse:
    try:
        result = _service().forecast(payload)
    except Exception as error:
        raise _prediction_error(error) from error

    _persist_forecast(db, payload, result)
    _commit(db)
    return ForecastResponse.model_validate(result)


@router.post(
    "/congestion",
    response_model=CongestionResponse,
    dependencies=[Depends(require_roles(*OPERATIONAL_ROLES))],
)
def congestion(
    payload: ERPredictionInput,
    db: DatabaseSession,
    _: CurrentUser,
) -> CongestionResponse:
    try:
        result = _service().congestion(payload)
    except Exception as error:
        raise _prediction_error(error) from error

    _persist_congestion(db, payload, result)
    _commit(db)
    return CongestionResponse.model_validate(result)


@router.post(
    "/resources",
    response_model=ResourceResponse,
    dependencies=[Depends(require_roles(*OPERATIONAL_ROLES))],
)
def resources(
    payload: ERPredictionInput,
    db: DatabaseSession,
    _: CurrentUser,
) -> ResourceResponse:
    try:
        result = _service().resources(payload)
    except Exception as error:
        raise _prediction_error(error) from error

    _persist_resources(db, payload, result)
    _commit(db)
    return ResourceResponse.model_validate(result)


@router.post(
    "/run",
    response_model=CombinedPredictionResponse,
    dependencies=[Depends(require_roles(*OPERATIONAL_ROLES))],
)
def run_predictions(
    payload: ERPredictionInput,
    db: DatabaseSession,
    _: CurrentUser,
) -> CombinedPredictionResponse:
    try:
        service = _service()
        forecast_result = service.forecast(payload)
        congestion_result = service.congestion(payload)
        resource_result = service.resources(payload)

        score_result = calculate_congestion_score(
            payload,
            forecast_result,
            congestion_result,
            resource_result,
        )
    except Exception as error:
        raise _prediction_error(error) from error

    _persist_forecast(db, payload, forecast_result)
    _persist_congestion(db, payload, congestion_result)
    _persist_resources(db, payload, resource_result)

    combined = CombinedPredictionResponse(
        timestamp=payload.timestamp,
        forecast=forecast_result,
        congestion=congestion_result,
        resources=resource_result,
        congestion_score=score_result,
    )

    db.add(
        AIAssessment(
            er_unit_id=payload.er_unit_id,
            requested_by_user_id=_.id,
            assessment_timestamp=payload.timestamp,
            input_payload=jsonable_encoder(
                payload.model_dump(mode="json")
            ),
            prediction_payload=jsonable_encoder(
                combined.model_dump(mode="json")
            ),
            congestion_score=score_result["score"],
            congestion_level=score_result["level"].value,
        )
    )

    _commit(db)
    return combined


@router.get(
    "/assessments/history",
    response_model=AIAssessmentHistoryResponse,
    dependencies=[Depends(require_roles(*OPERATIONAL_ROLES))],
)
def assessment_history(
    db: DatabaseSession,
    _: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AIAssessmentHistoryResponse:
    query = (
        select(AIAssessment)
        .order_by(
            desc(AIAssessment.created_at),
            desc(AIAssessment.id),
        )
        .offset(offset)
        .limit(limit)
    )

    rows = db.scalars(query).all()
    total = db.scalar(
        select(func.count()).select_from(AIAssessment)
    ) or 0

    return AIAssessmentHistoryResponse(
        assessments=[
            AIAssessmentHistoryItem.model_validate(row)
            for row in rows
        ],
        count=total,
    )


@router.get(
    "/latest",
    response_model=LatestPredictionResponse,
    dependencies=[Depends(require_roles(*OPERATIONAL_ROLES))],
)
def latest_predictions(
    db: DatabaseSession,
    _: CurrentUser,
) -> LatestPredictionResponse:
    predictions = db.scalars(
        select(Prediction)
        .order_by(desc(Prediction.created_at))
        .limit(50)
    ).all()

    resources = db.scalars(
        select(ResourcePrediction)
        .order_by(desc(ResourcePrediction.target_timestamp))
        .limit(10)
    ).all()

    timestamp = (
        predictions[0].created_at
        if predictions
        else (
            resources[0].target_timestamp
            if resources
            else None
        )
    )

    if timestamp is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "no_predictions",
                "message": "No predictions have been generated",
            },
        )

    return LatestPredictionResponse(
        timestamp=timestamp,
        forecasts=[
            {
                "type": item.prediction_type,
                "target_timestamp": item.target_timestamp,
                "value": item.predicted_value,
                "congestion_level": item.congestion_level,
                "confidence": item.confidence,
                "model_version": item.model_version,
            }
            for item in predictions
        ],
        resources=[
            {
                "target_timestamp": item.target_timestamp,
                "required_beds": item.required_beds,
                "required_doctors": item.required_doctors,
                "required_nurses": item.required_nurses,
                "model_version": item.model_version,
            }
            for item in resources
        ],
    )


@models_router.get(
    "/status",
    response_model=ModelStatusResponse,
    dependencies=[Depends(require_roles(*OPERATIONAL_ROLES))],
)
def model_status(_: CurrentUser) -> ModelStatusResponse:
    return ModelStatusResponse(models=_service().status())


# --------------------------------------------------
# WAIT-TIME PREDICTION ENDPOINT
# --------------------------------------------------

class WaitTimePredictionInput(BaseModel):
    timestamp: datetime
    patient_gender: str
    patient_age: int = Field(ge=0, le=120)
    patient_race: str
    department_referral: str


@lru_cache(maxsize=1)
def _load_waittime_model():
    model_path = (
        Path(__file__).resolve().parents[4]
        / "ML"
        / "smarter_waittime_model.joblib"
    )

    if not model_path.exists():
        raise FileNotFoundError(
            f"Wait-time model not found at {model_path}"
        )

    return joblib.load(model_path)


@router.post(
    "/waittime",
    dependencies=[Depends(require_roles(*OPERATIONAL_ROLES))],
)
def predict_waittime(
    payload: WaitTimePredictionInput,
    _: CurrentUser,
):
    try:
        timestamp = payload.timestamp

        features = pd.DataFrame(
            [
                {
                    "patient_gender": payload.patient_gender,
                    "patient_age": payload.patient_age,
                    "patient_race": payload.patient_race,
                    "department_referral": payload.department_referral,
                    "hour": timestamp.hour,
                    "day_of_week": timestamp.weekday(),
                    "month": timestamp.month,
                    "is_weekend": int(timestamp.weekday() >= 5),
                }
            ]
        )

        model = _load_waittime_model()
        prediction = float(model.predict(features)[0])

        return {
            "predicted_waittime_minutes": round(
                max(0.0, prediction), 2
            ),
            "model_name": "RandomForestRegressor",
            "unit": "minutes",
        }

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wait-time prediction failed. Check backend logs.",
        ) from error
