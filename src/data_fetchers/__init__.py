import asyncio
import aiohttp
import logging
from typing import List

from .dx_summit import DXSummitFetcher
from .dx_cluster import DXClusterFetcher
from .dx_news import DXNewsFetcher
from .base import BaseFetcher
from ..models import DXStation
from ..config import Config

logger = logging.getLogger(__name__)


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

