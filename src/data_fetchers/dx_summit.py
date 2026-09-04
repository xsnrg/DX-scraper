import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from urllib.parse import urlencode

import aiohttp

from .base import BaseFetcher
from ..bands import frequency_to_band, mode_from_text
from ..models import DXStation, live_spot_key

logger = logging.getLogger(__name__)


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
        self.spots_limit = 250

    def _parse_spots_csv(self, csv_data: str) -> List[Dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(csv_data))
        return list(reader)

    def _parse_spots(self, data: str) -> List[Dict[str, Any]]:
        text = (data or "").lstrip()
        if text.startswith("[") or text.startswith("{"):
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                parsed = parsed.get("spots") or parsed.get("data") or []
            if not isinstance(parsed, list):
                return []
            return parsed
        return self._parse_spots_csv(data)

    async def fetch(self) -> List[DXStation]:
        params = {
            "limit": self.spots_limit,
            "include": "HF",
        }
        url = f"{self.api_url}?{urlencode(params)}"
        headers = {
            "User-Agent": "DX-scraper (https://github.com/xsnrg/DX-scraper)",
            "Accept": "application/json, text/csv;q=0.8, */*;q=0.5",
        }

        body = await self.fetch_with_retry(url, headers=headers)
        if not body:
            return []

        try:
            spots = self._parse_spots(body)
        except (json.JSONDecodeError, csv.Error, ValueError) as e:
            logger.error(f"DX Summit: failed to parse spots: {e}")
            return []

        stations_map: Dict[tuple, DXStation] = {}

        for spot in spots:
            try:
                dx_call = (spot.get("dx_call") or "").strip()
                if not dx_call:
                    continue

                frequency = float(spot.get("frequency") or 0) / 1000.0
                if frequency <= 0:
                    frequency = None

                last_update = _parse_time(spot.get("time", ""))

                band = (spot.get("band") or "").strip()
                if not band and frequency:
                    band = frequency_to_band(frequency) or ""

                info = spot.get("info") or ""
                mode = (spot.get("mode") or "").strip() or mode_from_text(info)
                dx_country = spot.get("dx_country") or ""
                spotter = (spot.get("de_call") or spot.get("spotter") or "").strip()

                key = live_spot_key(dx_call, band, mode, frequency)
                existing = stations_map.get(key)
                if existing is not None:
                    if mode and not existing.mode:
                        existing.mode = mode
                    continue

                stations_map[key] = DXStation(
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

        logger.info(f"DX Summit: {len(stations_map)} live spots")
        return list(stations_map.values())
