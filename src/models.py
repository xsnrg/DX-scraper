from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime, timezone


class DXStation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    callsign: str
    name: str
    location: str
    frequency: Optional[float] = None
    bands: list[str] = Field(default_factory=list)
    active_band: Optional[str] = None
    active_mode: Optional[str] = None
    last_update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=timezone.utc))
    source: str
    status: str = "active"

    @field_validator("callsign")
    @classmethod
    def validate_callsign(cls, v):
        if not v.strip():
            raise ValueError("callsign cannot be empty or whitespace only")
        return v


class DXDataSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_stations: int
    active_stations: int
    last_refresh: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=timezone.utc))
    data_sources: list[str]
    stations: list[DXStation]
