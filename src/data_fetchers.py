import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import logging
import feedparser
import csv
import io
from urllib.parse import urlencode

from .models import DXStation
from .exceptions import DataSourceError, DataStalenessException
from .config import Config

logger = logging.getLogger(__name__)


class BaseFetcher:
    def __init__(self, name: str, session: aiohttp.ClientSession):
        self.name = name
        self.session = session
        self.retry_attempts = Config.RETRY_ATTEMPTS
        self.retry_delay = Config.RETRY_DELAY_SECONDS

    async def fetch_with_retry(self, url: str, headers: Dict[str, str] = None) -> Optional[str]:
        for attempt in range(self.retry_attempts):
            try:
                async with self.session.get(url, headers=headers, timeout=Config.REQUEST_TIMEOUT) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning(f"{self.name}: HTTP {response.status} on attempt {attempt + 1}")
                    await asyncio.sleep(self.retry_delay)
            except asyncio.TimeoutError:
                logger.warning(f"{self.name}: Timeout on attempt {attempt + 1}")
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"{self.name}: Error on attempt {attempt + 1}: {e}")
                await asyncio.sleep(self.retry_delay)
        
        raise DataSourceError(self.name, f"Failed after {self.retry_attempts} attempts")

    def validate_age(self, last_update: datetime) -> bool:
        max_age = timedelta(seconds=Config.DATA_MAX_AGE_SECONDS)
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - last_update
        if age > max_age:
            raise DataStalenessException(Config.DATA_MAX_AGE_SECONDS, int(age.total_seconds()))
        return True


class DXSummitFetcher(BaseFetcher):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__("DX Summit", session)
        self.api_url = "http://www.dxsummit.fi/api/v1/spots"
        self.spots_limit = 100

    def _frequency_to_bands(self, frequency: float) -> List[str]:
        freq_mhz = frequency / 1000000.0
        bands = []
        
        if 1.8 <= freq_mhz < 2.0:
            bands.append("160m")
        elif 3.5 <= freq_mhz < 4.0:
            bands.append("80m")
        elif 7.0 <= freq_mhz < 7.3:
            bands.append("40m")
        elif 10.1 <= freq_mhz < 10.15:
            bands.append("30m")
        elif 14.0 <= freq_mhz < 14.35:
            bands.append("20m")
        elif 18.06 <= freq_mhz < 18.168:
            bands.append("17m")
        elif 21.0 <= freq_mhz < 21.45:
            bands.append("15m")
        elif 24.89 <= freq_mhz < 24.99:
            bands.append("12m")
        elif 28.0 <= freq_mhz < 29.7:
            bands.append("10m")
        elif 50.0 <= freq_mhz < 54.0:
            bands.append("6m")
        
        return bands

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
                bands = self._frequency_to_bands(frequency)
                
                try:
                    last_update = datetime.fromisoformat(spot.get("time", "").replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    last_update = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
                
                if not self.validate_age(last_update):
                    continue
                
                stations_map[dx_call] = DXStation(
                    callsign=dx_call,
                    name=spot.get("info", "")[:50] if spot.get("info") else "",
                    location=spot.get("dx_country", ""),
                    bands=bands,
                    active_band=bands[0] if bands else None,
                    active_mode=None,
                    last_update=last_update,
                    source="DX Summit"
                )
            except Exception as e:
                logger.error(f"Error parsing DX Summit spot: {e}")
                continue
        
        return list(stations_map.values())


class DXClusterFetcher(BaseFetcher):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__("DX Cluster", session)

    async def fetch(self) -> List[DXStation]:
import asyncio
from typing import List, Dict, Optional
import aiohttp

class BaseFetcher:
    def __init__(self, name: str, session: aiohttp.ClientSession):
        self.name = name
        self.session = session
        self.retry_attempts = Config.RETRY_ATTEMPTS
        self.retry_delay = Config.RETRY_DELAY_SECONDS

    @staticmethod
    def frequency_to_bands(frequency: float) -> List[str]:
        freq_mhz = frequency / 1000000.0
        bands = []
        if 1.8 <= freq_mhz < 2.0: bands.append("160m")
        elif 3.5 <= freq_mhz < 4.0: bands.append("80m")
        elif 7.0 <= freq_mhz < 7.3: bands.append("40m")
        elif 10.1 <= freq_mhz < 10.15: bands.append("30m")
        elif 14.0 <= freq_mhz < 14.35: bands.append("20m")
        elif 18.06 <= freq_mhz < 18.168: bands.append("17m")
        elif 21.0 <= freq_mhz < 21.45: bands.append("15m")
        elif 24.89 <= freq_mhz < 24.99: bands.append("12m")
        elif 28.0 <= freq_mhz < 29.7: bands.append("10m")
        elif 50.0 <= freq_mhz < 54.0: bands.append("6m")
        return bands

    async def fetch_with_retry(self, url: str, headers: Dict[str, str] = None) -> Optional[str]:
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
                    source="DX Cluster"
                ))
            except Exception as e:
                logger.error(f"Error parsing DX Cluster row: {e}")
                continue
        
        return stations


class DXNewsFetcher(BaseFetcher):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__("DXNews", session)

    async def fetch(self) -> List[DXStation]:
        feed = await self.fetch_with_retry("https://dxnews.com/rss.xml")
        if not feed:
            return []
        
        try:
            parsed_feed = feedparser.parse(feed)
            stations = []
            
            for entry in parsed_feed.entries:
                try:
                    title = entry.title.replace(". From DXNews.com", "").strip()
                    callsign = title.split()[0] if title else None
                    
                    if not callsign:
                        continue
                    
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    else:
                        pub_date = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
                    
                    description = entry.description if hasattr(entry, 'description') else ""
                    
                    stations.append(DXStation(
                        callsign=callsign,
                        name="DX News",
                        location=description[:50] if description else "",
                        bands=[],
                        active_band=None,
                        active_mode=None,
                        last_update=pub_date,
                        source="DXNews"
                    ))
                except Exception as e:
                    logger.error(f"Error parsing DXNews entry: {e}")
                    continue
            
            return stations
        except Exception as e:
            logger.error(f"Error parsing DXNews feed: {e}")
            return []


async def fetch_all_data() -> List[DXStation]:
    async with aiohttp.ClientSession() as session:
        fetchers = []
        if Config.DATA_SOURCES["dx_summit"]["enabled"]:
            fetchers.append(DXSummitFetcher(session))
        if Config.DATA_SOURCES["dxcluster"]["enabled"]:
            fetchers.append(DXClusterFetcher(session))
        if Config.DATA_SOURCES["dxnews"]["enabled"]:
            fetchers.append(DXNewsFetcher(session))
        
        all_stations = []
        tasks = [fetcher.fetch() for fetcher in fetchers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for fetcher, result in zip(fetchers, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching from {fetcher.name}: {result}")
            else:
                all_stations.extend(result)
        
        return all_stations
