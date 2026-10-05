from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    TRIAGE_NURSE = "TRIAGE_NURSE"
    HEALTH_AUTHORITY = "HEALTH_AUTHORITY"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.TRIAGE_NURSE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ERMetric(Base):
    __tablename__ = "er_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    er_unit_id: Mapped[str] = mapped_column(String(80), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    arrivals: Mapped[int] = mapped_column(Integer, default=0)
    departures: Mapped[int] = mapped_column(Integer, default=0)
    active_patients: Mapped[int] = mapped_column(Integer, default=0)
    waiting_patients: Mapped[int] = mapped_column(Integer, default=0)
    occupied_beds: Mapped[int] = mapped_column(Integer, default=0)
    available_beds: Mapped[int] = mapped_column(Integer, default=0)
    average_wait_minutes: Mapped[float] = mapped_column(Float, default=0)
    critical_patient_count: Mapped[int] = mapped_column(Integer, default=0)


class ExternalFactor(Base):
    __tablename__ = "external_factors"

    id: Mapped[int] = mapped_column(primary_key=True)
    er_unit_id: Mapped[str] = mapped_column(String(80), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    weather_category: Mapped[str | None] = mapped_column(String(40))
    temperature: Mapped[float | None] = mapped_column(Float)
    holiday_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    weekend_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    local_event_flag: Mapped[bool] = mapped_column(Boolean, default=False)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    er_unit_id: Mapped[str] = mapped_column(String(80), index=True)
    prediction_type: Mapped[str] = mapped_column(String(50))
    target_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    predicted_value: Mapped[float] = mapped_column(Float)
    congestion_level: Mapped[str | None] = mapped_column(String(20))
    congestion_score: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResourcePrediction(Base):
    __tablename__ = "resource_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    er_unit_id: Mapped[str] = mapped_column(String(80), index=True)
    target_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    required_beds: Mapped[int] = mapped_column(Integer)
    required_doctors: Mapped[int] = mapped_column(Integer)
    required_nurses: Mapped[int] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(80))


class AIAssessment(Base):
    __tablename__ = "ai_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    er_unit_id: Mapped[str] = mapped_column(String(80), index=True)
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assessment_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    input_payload: Mapped[dict] = mapped_column(JSON)
    prediction_payload: Mapped[dict] = mapped_column(JSON)
    congestion_score: Mapped[float] = mapped_column(Float)
    congestion_level: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    er_unit_id: Mapped[str] = mapped_column(String(80), index=True)
    alert_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    er_unit_id: Mapped[str] = mapped_column(String(80), index=True)
    priority: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(80))
    metric_name: Mapped[str] = mapped_column(String(80))
    metric_value: Mapped[float] = mapped_column(Float)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)