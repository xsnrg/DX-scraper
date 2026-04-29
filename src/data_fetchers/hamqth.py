import aiohttp
import logging
from typing import List
from datetime import datetime, timezone

from .base import BaseFetcher
from ..models import DXStation

logger = logging.getLogger(__name__)

class HamQTHFetcher(BaseFetcher):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__("HamQTH", session)

    async def fetch(self) -> List[DXStation]:
        url = "https://www.hamqth.com/dxc_csv.php?limit=100"
        text = await self.fetch_with_retry(url)
        if not text:
            return []

        stations = []
        lines = text.strip().splitlines()
        
        for line in lines:
            if not line:
                continue
            
            parts = line.split('^')
            if len(parts) < 10:
                continue
                
            try:
                # 0: Spotter, 1: Frequency, 2: Call (DX), 3: Comment, 4: Date/Time, 
                # 5: LoTW, 6: eQSL, 7: Continent, 8: Band, 9: Country, 10: ADIF
                spotter = parts[0].strip()
                frequency_str = parts[1].strip()
                callsign = parts[2].strip()
                comment = parts[3].strip()
                date_time_str = parts[4].strip()
                band = parts[8].strip()
                country = parts[9].strip()

                if not callsign:
                    continue

                try:
                    dt_parts = date_time_str.split(' ')
                    if len(dt_parts) == 2:
                        time_str, date_str = dt_parts
                        formatted_dt = f"{date_str} {time_str[:2]}:{time_str[2:]}"
                        last_update = datetime.strptime(formatted_dt, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                    else:
                        last_update = datetime.now(timezone.utc)
                except Exception as e:
                    logger.debug(f"Could not parse date {date_time_str}: {e}")
                    last_update = datetime.now(timezone.utc)

                stations.append(DXStation(
                    callsign=callsign,
                    dx_country=country,
                    spotter_country="",
                    spotter=spotter,
                    band=band,
                    frequency=float(frequency_str) if frequency_str else None,
                    mode="",
                    comment=comment,
                    last_update=last_update,
                    source=self.name
                ))
            except Exception as e:
                logger.error(f"Error parsing HamQTH CSV line: {e}")
                continue

        return stations
