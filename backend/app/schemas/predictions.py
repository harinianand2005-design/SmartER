
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeatherCategory(StrEnum):
    CLEAR = "clear"
    RAIN = "rain"
    STORM = "storm"


class ERPredictionInput(BaseModel):
    timestamp: datetime
    patient_arrivals: int = Field(ge=0, le=1000)
    current_patients: int = Field(ge=0, le=500)
    available_beds: int = Field(ge=0, le=500)
    doctors_available: int = Field(ge=0, le=100)
    nurses_available: int = Field(ge=0, le=300)
    doctors_scheduled: int = Field(default=8, ge=1, le=100)
    nurses_scheduled: int = Field(default=18, ge=1, le=300)
    average_waiting_time: float = Field(ge=0, le=1440)
    triage_1: int = Field(ge=0, le=1000)
    triage_2: int = Field(ge=0, le=1000)
    triage_3: int = Field(ge=0, le=1000)
    triage_4: int = Field(ge=0, le=1000)
    triage_5: int = Field(ge=0, le=1000)
    temperature: float = Field(ge=-80, le=70)
    rainfall: float = Field(ge=0, le=500)
    holiday: int = Field(ge=0, le=1)
    local_event: int = Field(ge=0, le=1)
    flu_index: float = Field(ge=0, le=100)
    weather_category: WeatherCategory = WeatherCategory.CLEAR
    er_unit_id: str = Field(
        default="synthetic-er",
        min_length=1,
        max_length=80,
    )

    @field_validator(
        "triage_1",
        "triage_2",
        "triage_3",
        "triage_4",
        "triage_5",
    )
    @classmethod
    def triage_total_not_above_arrivals(cls, value: int, info):
        arrivals = info.data.get("patient_arrivals")
        if arrivals is not None and value > arrivals:
            raise ValueError(
                "each triage count cannot exceed patient_arrivals"
            )
        return value


class ForecastResponse(BaseModel):
    timestamp: datetime
    forecasts: dict[str, float]
    model_version: str


class CongestionResponse(BaseModel):
    timestamp: datetime
    congestion_level: str
    probabilities: dict[str, float]
    confidence: float
    model_version: str


class ResourceResponse(BaseModel):
    timestamp: datetime
    required_beds: float
    required_doctors: float
    required_nurses: float
    model_versions: dict[str, str]


class CombinedPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    forecast: ForecastResponse
    congestion: CongestionResponse
    resources: ResourceResponse
    congestion_score: dict[str, object] | None = None


class AIAssessmentHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    er_unit_id: str
    assessment_timestamp: datetime
    created_at: datetime
    input_payload: dict
    prediction_payload: dict
    congestion_score: float
    congestion_level: str


class AIAssessmentHistoryResponse(BaseModel):
    assessments: list[AIAssessmentHistoryItem]
    count: int


class LatestPredictionResponse(BaseModel):
    timestamp: datetime
    forecasts: list[dict]
    resources: list[dict]


class ModelStatus(BaseModel):
    model_name: str
    version: str | None
    loaded: bool
    artifact_name: str
    validation_metrics: dict | None = None
    test_metrics: dict | None = None
    error: str | None = None


class ModelStatusResponse(BaseModel):
    models: list[ModelStatus]
