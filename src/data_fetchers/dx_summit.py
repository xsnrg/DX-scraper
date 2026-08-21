import csv
import io
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List
from urllib.parse import urlencode

import aiohttp

from .base import BaseFetcher
from ..bands import frequency_to_band
from ..models import DXStation

logger = logging.getLogger(__name__)

# Modes commonly embedded in DX Summit `info` text (longest first).
_KNOWN_MODES = (
    "PSK31", "JT65", "JT9", "FT8", "FT4", "RTTY", "DIGI", "SSB", "CW", "AM", "FM",
)
_MODE_RE = re.compile(
    r"\b(" + "|".join(_KNOWN_MODES) + r")\b",
    re.IGNORECASE,
)


def _mode_from_info(info: str) -> str:
    match = _MODE_RE.search(info or "")
    return match.group(1).upper() if match else ""


def _parse_time(raw: str) -> datetime:
    try:
        last_update = datetime.fromisoformat((raw or "").replace("Z", "+00:00"))
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)
        return last_update
    except (ValueError, AttributeError, TypeError):
        return datetime.now(timezone.utc)


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
                dx_call = (spot.get("dx_call") or "").strip()
                if not dx_call:
                    continue

                if dx_call in stations_map:
                    continue

                frequency = float(spot.get("frequency") or 0) / 1000.0
                if frequency <= 0:
                    frequency = None

                last_update = _parse_time(spot.get("time", ""))

                band = (spot.get("band") or "").strip()
                if not band and frequency:
                    band = frequency_to_band(frequency) or ""

                info = spot.get("info") or ""
                mode = (spot.get("mode") or "").strip() or _mode_from_info(info)
                dx_country = spot.get("dx_country") or ""
                spotter = (spot.get("de_call") or spot.get("spotter") or "").strip()

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
