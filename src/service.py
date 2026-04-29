import logging
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .models import DXStation, DXDataSummary
from .data_fetchers import fetch_all_data
from .exceptions import DataStalenessException

logger = logging.getLogger(__name__)


class DXPeditionService:
    def __init__(self, max_age_seconds: int = 3600):
        self.max_age_seconds = max_age_seconds

    def filter_by_age(self, stations: List[DXStation]) -> List[DXStation]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.max_age_seconds)
        filtered = [s for s in stations if self._normalize_datetime(s.last_update) >= cutoff_time]
        
        if len(filtered) < len(stations):
            logger.info(f"Filtered {len(stations) - len(filtered)} stations older than {self.max_age_seconds}s")
        
        return filtered

    def deduplicate_stations(self, stations: List[DXStation]) -> List[DXStation]:
        seen: dict[str, DXStation] = {}
        sources: dict[str, set[str]] = {}
        for station in stations:
            if station.callsign not in seen:
                seen[station.callsign] = station
                sources[station.callsign] = {station.source}
            else:
                sources[station.callsign].add(station.source)
                existing = seen[station.callsign]
                if self._normalize_datetime(station.last_update) > self._normalize_datetime(existing.last_update):
                    seen[station.callsign] = station
        
        for callsign in seen:
            seen[callsign].sources = sorted(sources[callsign])
        
        return list(seen.values())

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
                stations = await fetch_all_data(session)

            stations = self.filter_by_age(stations)
            stations = self.deduplicate_stations(stations)
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

