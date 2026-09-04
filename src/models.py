from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime, timezone


def live_spot_key(
    callsign: str,
    band: str = "",
    mode: str = "",
    frequency: Optional[float] = None,
) -> tuple:
    """Identity of an on-air spot: one row per callsign + band + mode.

    DXpeditions commonly run several stations at once (20m CW, 17m FT8, …).
    Frequency is part of the key only when band or mode is missing, so two
    unmoded spots on different frequencies stay distinct while duplicate
    reports of the same station still collapse.
    """
    call = (callsign or "").upper().strip()
    band_n = (band or "").strip().lower()
    mode_n = (mode or "").strip().upper()
    if band_n and mode_n:
        return (call, band_n, mode_n)
    freq = ""
    if frequency is not None:
        try:
            freq = f"{round(float(frequency), 3):.3f}"
        except (TypeError, ValueError):
            freq = ""
    return (call, band_n, mode_n, freq)


def station_identity(station: "DXStation") -> tuple:
    """Dedup key for a station row.

    Potential (calendar) spots are one-per-callsign. Live spots are one row
    per concurrent station (callsign + band + mode).
    """
    call = station.callsign.upper().strip()
    if station.potential:
        return ("potential", call)
    return ("live",) + live_spot_key(
        station.callsign, station.band, station.mode, station.frequency
    )


class DXStation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    callsign: str
    dx_country: str = ""
    dxcc: str = ""
    spotter_country: str = ""
    spotter: str = ""
    band: str = ""
    frequency: Optional[float] = None
    mode: str = ""
    comment: str = ""
    last_update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=timezone.utc))
    source: str
    sources: list[str] = []
    pota_reference: str = ""
    status: str = "active"
    potential: bool = False

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
