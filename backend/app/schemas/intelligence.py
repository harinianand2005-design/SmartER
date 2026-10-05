from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.predictions import ERPredictionInput


class CongestionLevel(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IntelligenceRequest(ERPredictionInput):
    """Operational scenario used by intelligence endpoints."""


class ExplainModel(StrEnum):
    CONGESTION = "congestion_classifier"
    BEDS = "bed_prediction_model"
    DOCTORS = "doctor_prediction_model"
    NURSES = "nurse_prediction_model"


class ExplainRequest(BaseModel):
    model: ExplainModel
    scenario: IntelligenceRequest


class ScoreFactor(BaseModel):
    name: str
    value: float
    contribution: float
    explanation: str


class CongestionScoreResponse(BaseModel):
    score: float = Field(ge=0, le=100)
    level: CongestionLevel
    confidence: float | None = None
    timestamp: datetime
    factors: list[ScoreFactor]
    explanation: str


class ExplanationResponse(BaseModel):
    model_name: str
    model_version: str
    prediction: str | float
    base_value: float | None = None
    top_contributing_features: list[dict]
    timestamp: datetime
    interpretation: str


class RecommendationResponse(BaseModel):
    id: int | None = None
    priority: str
    title: str
    reason: str
    supporting_metric: str
    timestamp: datetime
    status: str = "OPEN"


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    severity: str
    title: str
    description: str
    trigger_value: float | None = None
    threshold: float | None = None
    timestamp: datetime
    status: str


class ResolveAlertRequest(BaseModel):
    status: str = "RESOLVED"
    
class WhatIfRequest(BaseModel):
    additional_beds: int = Field(ge=0)
    additional_doctors: int = Field(ge=0)
    additional_nurses: int = Field(ge=0)
    expected_arrival_change: float


class WhatIfResponse(BaseModel):
    demand_pressure: str
    additional_beds: int
    additional_doctors: int
    additional_nurses: int
    expected_arrival_change: float    