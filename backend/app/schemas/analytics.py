from datetime import datetime

from pydantic import BaseModel


class ObservedERMetric(BaseModel):
    timestamp: datetime
    arrivals: int
    active_patients: int
    waiting_patients: int
    available_beds: int
    occupied_beds: int
    average_wait_minutes: float
    occupancy_percentage: float | None


class ArrivalForecastPoint(BaseModel):
    target_timestamp: datetime
    horizon: str
    predicted_arrivals: float
    model_version: str


class CongestionHistoryPoint(BaseModel):
    target_timestamp: datetime
    congestion_level: str | None
    confidence: float | None
    model_version: str


class ResourceHistoryPoint(BaseModel):
    target_timestamp: datetime
    required_beds: int
    required_doctors: int
    required_nurses: int
    model_version: str


class AnalyticsSummary(BaseModel):
    observed_metric_count: int
    forecast_count: int
    congestion_prediction_count: int
    resource_prediction_count: int
    first_recorded_at: datetime | None
    last_recorded_at: datetime | None


class AnalyticsResponse(BaseModel):
    summary: AnalyticsSummary
    observed_metrics: list[ObservedERMetric]
    arrival_forecasts: list[ArrivalForecastPoint]
    congestion_history: list[CongestionHistoryPoint]
    resource_history: list[ResourceHistoryPoint]