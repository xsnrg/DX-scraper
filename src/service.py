import logging
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .models import DXStation, DXDataSummary, station_identity
from .data_fetchers import fetch_all_data
from .exceptions import DataStalenessException
from .bands import frequency_to_band
from .dxcc import resolve_dxcc

logger = logging.getLogger(__name__)


class DXPeditionService:
    def __init__(self, max_age_seconds: int = 3600, excluded_sources: Optional[List[str]] = None):
        self.max_age_seconds = max_age_seconds
        self.excluded_sources = excluded_sources or []

    def filter_by_age(self, stations: List[DXStation]) -> List[DXStation]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.max_age_seconds)
        filtered = [
            s for s in stations
            if s.potential or self._normalize_datetime(s.last_update) >= cutoff_time
        ]

        if len(filtered) < len(stations):
            logger.info(f"Filtered {len(stations) - len(filtered)} stations older than {self.max_age_seconds}s")

        return filtered

    def deduplicate_stations(self, stations: List[DXStation]) -> List[DXStation]:
        """Merge equivalent reports; keep concurrent stations of the same call.

        Live spots collapse by callsign + band + mode (a DXpedition running
        20m CW and 17m FT8 is two rows). Duplicate reports of the same
        station still merge, newest wins, POTA wins over a cluster report
        of the same station. A potential calendar row is dropped when any
        live spot exists for that callsign.
        """
        seen: dict[tuple, DXStation] = {}
        sources: dict[tuple, set[str]] = {}
        live_calls: set[str] = set()

        lives = [s for s in stations if not s.potential]
        potentials = [s for s in stations if s.potential]

        for station in lives:
            key = station_identity(station)
            live_calls.add(station.callsign.upper())
            if key not in seen:
                seen[key] = station
                sources[key] = {station.source}
                continue

            existing = seen[key]
            sources[key].add(station.source)
            if station.source == "POTA" and existing.source != "POTA":
                seen[key] = station
            elif self._normalize_datetime(station.last_update) > self._normalize_datetime(existing.last_update):
                seen[key] = station

        for station in potentials:
            if station.callsign.upper() in live_calls:
                continue
            key = station_identity(station)
            if key not in seen:
                seen[key] = station
                sources[key] = {station.source}
                continue
            existing = seen[key]
            sources[key].add(station.source)
            if self._normalize_datetime(station.last_update) > self._normalize_datetime(existing.last_update):
                seen[key] = station

        for key in seen:
            seen[key].sources = sorted(sources[key])

        return list(seen.values())

    def normalize_bands(self, stations: List[DXStation]) -> List[DXStation]:
        for station in stations:
            if not station.band and station.frequency:
                computed = frequency_to_band(float(station.frequency))
                if computed:
                    station.band = computed
        return stations

    def resolve_dxcc_numbers(self, stations: List[DXStation]) -> List[DXStation]:
        for station in stations:
            if station.source == "POTA":
                continue
            if station.dxcc:
                station.dxcc = station.dxcc.strip().lstrip("0") or ""
            else:
                station.dxcc = resolve_dxcc(station.dx_country) or ""
        return stations

    def _normalize_datetime(self, dt: datetime) -> datetime:
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

    def get_active_bands(self, stations: List[DXStation]) -> List[DXStation]:
        active = [s for s in stations if s.status == "active"]
        logger.info(f"Found {len(active)} active stations out of {len(stations)} total")
        return active

    async def get_current_data(self, max_age_seconds: Optional[int] = None) -> DXDataSummary:
        if max_age_seconds is not None:
            self.max_age_seconds = max_age_seconds
        
        try:
            async with aiohttp.ClientSession() as session:
                stations = await fetch_all_data(session, self.excluded_sources)

            stations = self.filter_by_age(stations)
            stations = self.normalize_bands(stations)
            stations = self.deduplicate_stations(stations)
            stations = self.resolve_dxcc_numbers(stations)
            stations = self.get_active_bands(stations)
            
            sources = list(set(s.source for s in stations))
            
            return DXDataSummary(
                total_stations=len(stations),
                active_stations=len([s for s in stations if s.status == "active"]),
                last_refresh=datetime.now(timezone.utc).replace(tzinfo=timezone.utc),
                data_sources=sources,
                stations=stations
            )
        except DataStalenessException as e:
            logger.error(f"Data staleness error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching DX data: {e}")
            raise

    def get_station_by_callsign(self, stations: List[DXStation], callsign: str) -> Optional[DXStation]:
        for station in stations:
            if station.callsign.upper() == callsign.upper():
                return station
        return None
