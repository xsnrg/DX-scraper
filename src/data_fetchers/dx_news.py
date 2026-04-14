import aiohttp
import logging
import feedparser
from typing import List
from datetime import datetime, timezone

from .base import BaseFetcher
from ..models import DXStation

logger = logging.getLogger(__name__)


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
