import aiohttp
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from .base import BaseFetcher
from ..models import DXStation

logger = logging.getLogger(__name__)


class PotaFetcher(BaseFetcher):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__("POTA", session)
        self.api_url = "https://api.pota.app/spot"

    async def fetch(self) -> List[DXStation]:
        json_data = await self.fetch_with_retry(self.api_url)
        if not json_data:
            return []

        import json
        spots = json.loads(json_data)

        stations_map: Dict[str, DXStation] = {}

        for spot in spots:
            try:
                activator = (spot.get("activator") or "").strip()
                if not activator:
                    continue

                if activator in stations_map:
                    continue

                freq = spot.get("frequency")
                if freq:
                    try:
                        f = float(freq)
                        if f == f and f != float('inf') and f != float('-inf'):
                            frequency = f
                        else:
                            frequency = None
                    except (ValueError, TypeError):
                        frequency = None
                else:
                    frequency = None

                try:
                    spot_time = spot.get("spotTime", "")
                    last_update = datetime.fromisoformat(spot_time)
                    if last_update.tzinfo is None:
                        last_update = last_update.replace(tzinfo=timezone.utc)
                except (ValueError, AttributeError):
                    last_update = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)

                if not self.validate_age(last_update):
                    continue

                mode = (spot.get("mode") or "").strip()
                comments = (spot.get("comments") or "").strip()
                location_desc = (spot.get("locationDesc") or "").strip()
                reference = (spot.get("reference") or "").strip()
                spotter = (spot.get("spotter") or "").strip()

                if not location_desc and not reference:
                    continue

                dx_location = ""
                if location_desc and reference:
                    dx_location = f"{location_desc}, {reference}"
                elif location_desc:
                    dx_location = location_desc
                elif reference:
                    dx_location = reference

                combined_mode_comment = ""
                if mode:
                    combined_mode_comment = mode
                if comments:
                    if combined_mode_comment:
                        combined_mode_comment += f" | {comments}"
                    else:
                        combined_mode_comment = comments

                stations_map[activator] = DXStation(
                    callsign=activator,
                    dx_country=dx_location,
                    spotter_country="",
                    spotter=spotter,
                    band="",
                    frequency=frequency,
                    mode=mode,
                    comment=comments[:100],
                    last_update=last_update,
                    source="POTA",
                    pota_reference=reference
                )
            except Exception as e:
                logger.error(f"Error parsing POTA spot: {e}")
                continue

        if not stations_map:
            return []

        self.validate_all_stations(list(stations_map.values()))
        return list(stations_map.values())
