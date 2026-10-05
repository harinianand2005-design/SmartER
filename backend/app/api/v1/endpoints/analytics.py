from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession, require_roles
from app.models import ERMetric, Prediction, ResourcePrediction, UserRole
from app.schemas.analytics import (
    AnalyticsResponse,
    AnalyticsSummary,
    ArrivalForecastPoint,
    CongestionHistoryPoint,
    ObservedERMetric,
    ResourceHistoryPoint,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])
ANALYTICS_ROLES = (UserRole.ADMIN, UserRole.HEALTH_AUTHORITY)


def _time_filter(query, column, start: datetime | None, end: datetime | None):
    if start is not None:
        query = query.where(column >= start)
    if end is not None:
        query = query.where(column <= end)
    return query


@router.get("/summary", response_model=AnalyticsResponse, dependencies=[Depends(require_roles(*ANALYTICS_ROLES))])
def analytics_summary(
    db: DatabaseSession,
    _: CurrentUser,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    er_unit_id: str | None = Query(default=None, min_length=1, max_length=80),
) -> AnalyticsResponse:
    if start and end and start > end:
        raise HTTPException(status_code=422, detail={"code": "invalid_date_range", "message": "start must be earlier than or equal to end"})

    metrics_query = _time_filter(select(ERMetric), ERMetric.timestamp, start, end)
    forecast_query = _time_filter(select(Prediction).where(Prediction.prediction_type.like("arrival_forecast_%")), Prediction.target_timestamp, start, end)
    congestion_query = _time_filter(select(Prediction).where(Prediction.prediction_type == "congestion"), Prediction.target_timestamp, start, end)
    resource_query = _time_filter(select(ResourcePrediction), ResourcePrediction.target_timestamp, start, end)
    if er_unit_id:
        metrics_query = metrics_query.where(ERMetric.er_unit_id == er_unit_id)
        forecast_query = forecast_query.where(Prediction.er_unit_id == er_unit_id)
        congestion_query = congestion_query.where(Prediction.er_unit_id == er_unit_id)
        resource_query = resource_query.where(ResourcePrediction.er_unit_id == er_unit_id)

    observed_rows = db.scalars(metrics_query.order_by(ERMetric.timestamp).limit(2000)).all()
    forecast_rows = db.scalars(forecast_query.order_by(Prediction.target_timestamp).limit(2000)).all()
    congestion_rows = db.scalars(congestion_query.order_by(Prediction.target_timestamp).limit(2000)).all()
    resource_rows = db.scalars(resource_query.order_by(ResourcePrediction.target_timestamp).limit(2000)).all()

    observed = []
    for row in observed_rows:
        capacity = row.occupied_beds + row.available_beds
        observed.append(ObservedERMetric(timestamp=row.timestamp, arrivals=row.arrivals, active_patients=row.active_patients, waiting_patients=row.waiting_patients, available_beds=row.available_beds, occupied_beds=row.occupied_beds, average_wait_minutes=row.average_wait_minutes, occupancy_percentage=(row.occupied_beds / capacity * 100 if capacity else None)))
    forecasts = [ArrivalForecastPoint(target_timestamp=row.target_timestamp, horizon=row.prediction_type.removeprefix("arrival_forecast_"), predicted_arrivals=row.predicted_value, model_version=row.model_version) for row in forecast_rows]
    congestion = [CongestionHistoryPoint(target_timestamp=row.target_timestamp, congestion_level=row.congestion_level, confidence=row.confidence, model_version=row.model_version) for row in congestion_rows]
    resources = [ResourceHistoryPoint(target_timestamp=row.target_timestamp, required_beds=row.required_beds, required_doctors=row.required_doctors, required_nurses=row.required_nurses, model_version=row.model_version) for row in resource_rows]
    recorded_timestamps = [row.timestamp for row in observed_rows] + [row.target_timestamp for row in forecast_rows] + [row.target_timestamp for row in congestion_rows] + [row.target_timestamp for row in resource_rows]
    return AnalyticsResponse(
        summary=AnalyticsSummary(observed_metric_count=len(observed), forecast_count=len(forecasts), congestion_prediction_count=len(congestion), resource_prediction_count=len(resources), first_recorded_at=min(recorded_timestamps) if recorded_timestamps else None, last_recorded_at=max(recorded_timestamps) if recorded_timestamps else None),
        observed_metrics=observed,
        arrival_forecasts=forecasts,
        congestion_history=congestion,
        resource_history=resources,
    )