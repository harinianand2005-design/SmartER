from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import CurrentUser, DatabaseSession, require_roles
from app.models import ERMetric, UserRole
from app.schemas.metrics import ERMetricCreate, ERMetricResponse

router = APIRouter(prefix="/er-metrics", tags=["operational metrics"])
INGEST_ROLES = (UserRole.ADMIN, UserRole.TRIAGE_NURSE)


@router.post("", response_model=ERMetricResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(*INGEST_ROLES))])
def ingest_er_metric(payload: ERMetricCreate, db: DatabaseSession, _: CurrentUser) -> ERMetricResponse:
    metric = ERMetric(**payload.model_dump())
    try:
        db.add(metric)
        db.commit()
        db.refresh(metric)
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail={"code": "database_unavailable", "message": "Operational metric could not be persisted"}) from error
    response_data = {column.name: getattr(metric, column.name) for column in ERMetric.__table__.columns}
    if response_data["timestamp"].tzinfo is None:
        response_data["timestamp"] = response_data["timestamp"].replace(tzinfo=timezone.utc)
    return ERMetricResponse.model_validate(response_data)