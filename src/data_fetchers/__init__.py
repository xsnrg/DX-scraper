import asyncio
import aiohttp
import logging
from typing import List

from .dx_cluster import DXClusterFetcher
from .dx_news import DXNewsFetcher
from .dx_summit import DXSummitFetcher
from .hamqth import HamQTHFetcher
from .base import BaseFetcher
from ..models import DXStation
from ..config import Config

__all__ = [
    "DXClusterFetcher",
    "DXNewsFetcher",
    "DXSummitFetcher",
    "HamQTHFetcher",
]

logger = logging.getLogger(__name__)


async def fetch_all_data(session: aiohttp.ClientSession) -> List[DXStation]:
    enabled_sources = Config.get_enabled_sources()
    fetchers_map = {
        "dx_cluster": DXClusterFetcher,
        "dx_news": DXNewsFetcher,
        "dx_summit": DXSummitFetcher,
        "hamqth": HamQTHFetcher,
    }

    fetchers = [
        fetchers_map[source](session)
        for source in enabled_sources
    ]
    all_stations = []
    tasks = [fetcher.fetch() for fetcher in fetchers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for fetcher, result in zip(fetchers, results):
        if isinstance(result, Exception):
            logger.error(f"Error fetching from {fetcher.name}: {result}")
        else:
            all_stations.extend(result)
    
    return all_stations

