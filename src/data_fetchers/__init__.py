import asyncio
import aiohttp
import logging
from typing import List, Optional

from .dx_cluster import DXClusterFetcher
from .dx_news import DXNewsFetcher
from .dx_summit import DXSummitFetcher
from .hamqth import HamQTHFetcher
from .pota import PotaFetcher
from .base import BaseFetcher
from ..models import DXStation
from ..config import Config

__all__ = [
    "DXClusterFetcher",
    "DXNewsFetcher",
    "DXSummitFetcher",
    "HamQTHFetcher",
    "PotaFetcher",
]

logger = logging.getLogger(__name__)


async def fetch_all_data(session: aiohttp.ClientSession, excluded_sources: Optional[List[str]] = None) -> List[DXStation]:
    enabled_sources = Config.get_enabled_sources()
    excluded_sources = {s.upper() for s in (excluded_sources or [])}
    fetchers_map = {
        "dx_cluster": DXClusterFetcher,
        "dx_news": DXNewsFetcher,
        "dx_summit": DXSummitFetcher,
        "hamqth": HamQTHFetcher,
        "pota": PotaFetcher,
    }

    fetchers = [
        fetchers_map[source](session)
        for source in enabled_sources
        if source.upper() not in excluded_sources
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

