import asyncio
import aiohttp
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone

from ..config import Config
from ..exceptions import DataSourceError, DataStalenessException

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
            return False
        return True

    def validate_all_stations(self, stations: list) -> None:
        if not stations:
            raise DataStalenessException(Config.DATA_MAX_AGE_SECONDS, 0)

