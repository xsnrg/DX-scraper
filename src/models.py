from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class DXStation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    callsign: str
    name: str
    location: str
    bands: list[str] = Field(default_factory=list)
    active_band: Optional[str] = None
    active_mode: Optional[str] = None
    last_update: datetime
    source: str
    status: str = "active"

class DXDataSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_stations: int
    active_stations: int
    last_refresh: datetime
    data_sources: list[str]
    stations: list[DXStation]

