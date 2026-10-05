
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ERMetricCreate(BaseModel):
    er_unit_id: str = Field(min_length=1, max_length=80)
    timestamp: datetime
    arrivals: int = Field(ge=0, le=5000)
    departures: int = Field(ge=0, le=5000)
    active_patients: int = Field(ge=0, le=5000)
    waiting_patients: int = Field(ge=0, le=5000)
    occupied_beds: int = Field(ge=0, le=2000)
    available_beds: int = Field(ge=0, le=2000)
    average_wait_minutes: float = Field(ge=0, le=1440)
    critical_patient_count: int = Field(ge=0, le=5000)


class ERMetricResponse(ERMetricCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
