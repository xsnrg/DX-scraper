import asyncio
import aiohttp
import csv
import io
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from urllib.parse import urlencode

from .base import BaseFetcher
from ..models import DXStation
from ..config import Config

logger = logging.getLogger(__name__)


class DXSummitFetcher(BaseFetcher):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__("DX Summit", session)
        self.api_url = "http://www.dxsummit.fi/api/v1/spots"
        self.spots_limit = 100

    def _parse_spots_csv(self, csv_data: str) -> List[Dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(csv_data))
        return list(reader)

    async def fetch(self) -> List[DXStation]:
        to_time = int(datetime.now(timezone.utc).timestamp())
        from_time = to_time - (24 * 60 * 60)
        
        params = {
            "limit": self.spots_limit,
            "from_time": from_time,
            "to_time": to_time,
            "content_type": "csv",
            "as_file": "true"
        }
        
        url = f"{self.api_url}?{urlencode(params)}"

        csv_data = await self.fetch_with_retry(url)
        if not csv_data:
            return []
        
        spots = self._parse_spots_csv(csv_data)
        
        stations_map: Dict[str, DXStation] = {}
        
        for spot in spots:
            try:
                dx_call = spot.get("dx_call", "").strip()
                if not dx_call:
                    continue
                
                if dx_call in stations_map:
                    continue
                
                frequency = float(spot.get("frequency", 0))
                
                try:
                    last_update = datetime.fromisoformat(spot.get("time", "").replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    last_update = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
                
                band = spot.get("band", "").strip()
                mode = spot.get("mode", "").strip()
                info = spot.get("info", "") or ""
                dx_country = spot.get("dx_country", "") or ""
                spotter = spot.get("spotter", "") or ""

                stations_map[dx_call] = DXStation(
                    callsign=dx_call,
                    dx_country=dx_country,
                    spotter_country="",
                    spotter=spotter,
                    band=band,
                    frequency=frequency,
                    mode=mode,
                    comment=info[:100],
                    last_update=last_update,
                    source="DX Summit"
                )
            except Exception as e:
                logger.error(f"Error parsing DX Summit spot: {e}")
                continue
        
        return list(stations_map.values())
