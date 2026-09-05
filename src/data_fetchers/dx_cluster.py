import aiohttp
import logging
from typing import List, Dict, Any

from .base import BaseFetcher
from ..models import DXStation, live_spot_key
from ..timeutil import parse_utc

logger = logging.getLogger(__name__)


class DXClusterFetcher(BaseFetcher):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__("Spothole", session)
        self.api_url = "https://spothole.app/api/v1/spots"
        self.spots_limit = 1000

    def _parse_spots_json(self, json_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return json_data

    async def fetch(self) -> List[DXStation]:
        json_data = await self.fetch_with_retry(self.api_url)
        if not json_data:
            return []
        
        import json
        spots = json.loads(json_data)
        
        stations_map: Dict[tuple, DXStation] = {}
        
        for spot in spots:
            try:
                dx_call = (spot.get("dx_call") or "").strip()
                if not dx_call or dx_call.startswith("#"):
                    continue
                
                freq = spot.get("freq")
                if freq:
                    try:
                        f = float(freq)
                        if f == f and f != float('inf') and f != float('-inf'):
                            frequency = f / 1000000.0
                        else:
                            frequency = None
                    except (ValueError, TypeError):
                        frequency = None
                else:
                    frequency = None
                
                last_update = parse_utc(spot.get("time_iso", ""), fallback_now=True)
                
                if not self.validate_age(last_update):
                    continue
                
                band = (spot.get("band") or "").strip()
                mode = (spot.get("mode") or "").strip()
                comment = spot.get("comment") or ""
                dx_country = spot.get("dx_country") or ""
                spotter = (spot.get("de_call") or "").strip()

                if not band and frequency is None:
                    continue

                key = live_spot_key(dx_call, band, mode, frequency)
                if key in stations_map:
                    continue

                stations_map[key] = DXStation(
                    callsign=dx_call,
                    dx_country=dx_country,
                    spotter_country="",
                    spotter=spotter,
                    band=band,
                    frequency=frequency,
                    mode=mode,
                    comment=comment[:100],
                    last_update=last_update,
                    source="Spothole"
                )
            except Exception as e:
                logger.error(f"Error parsing DX Cluster spot: {e}")
                continue
        
        self.validate_all_stations(list(stations_map.values()))
        return list(stations_map.values())
