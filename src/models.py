from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime

from .bands import canonical_band
from .timeutil import utc_now


def live_spot_key(
    callsign: str,
    band: str = "",
    mode: str = "",
    frequency: Optional[float] = None,
) -> tuple:
    """Identity of an on-air station: one row per callsign + kHz.

    DXpeditions run several stations at once (20m CW, 20m FT8, 30m FT8).
    Frequency is the on-air identity; 1 kHz rounding collapses slightly
    different reports of the same signal. Band/mode are used only when
    frequency is missing.
    """
    call = (callsign or "").upper().strip()
    if frequency is not None:
        try:
            khz = int(round(float(frequency) * 1000))
            if khz > 0:
                return (call, khz)
        except (TypeError, ValueError):
            pass
    band_n = canonical_band(band)
    mode_n = (mode or "").strip().upper()
    return (call, band_n, mode_n)


def station_identity(station: "DXStation") -> tuple:
    """Dedup key for a station row.

    Potential (calendar) spots are one-per-callsign. Live spots are one row
    per concurrent station (callsign + frequency).
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
    last_update: datetime = Field(default_factory=utc_now)
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
    last_refresh: datetime = Field(default_factory=utc_now)
    data_sources: list[str]
    stations: list[DXStation]
