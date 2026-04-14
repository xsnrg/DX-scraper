import aiohttp
import logging
from typing import List
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from .base import BaseFetcher
from ..models import DXStation

logger = logging.getLogger(__name__)


class HamQSLFetcher(BaseFetcher):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__("HamQSL", session)

    async def fetch(self) -> List[DXStation]:
        html = await self.fetch_with_retry("https://www.hamqsl.com/sq700.php")
        soup = BeautifulSoup(html, "lxml")
        
        stations = []
        for row in soup.find_all("tr"):
            try:
                cells = row.find_all("td")
                if len(cells) < 4:
                    continue
                
                callsign = cells[0].get_text(strip=True)
                if not callsign or callsign.startswith("#"):
                    continue
                
                name = cells[1].get_text(strip=True)
                location = cells[2].get_text(strip=True)
                last_update_str = cells[3].get_text(strip=True)
                
                try:
                    last_update = datetime.strptime(last_update_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    last_update = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
                
                if not self.validate_age(last_update):
                    continue
                
                stations.append(DXStation(
                    callsign=callsign,
                    name=name,
                    location=location,
                    bands=[],
                    active_band=None,
                    active_mode=None,
                    last_update=last_update,
                    source="HamQSL"
                ))
            except Exception as e:
                logger.error(f"Error parsing HamQSL row: {e}")
                continue
        
        return stations
