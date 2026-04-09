import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, urlparse
from data_fetchers import (
    BaseFetcher,
    DXSummitFetcher,
    DXClusterFetcher,
    HamQSLFetcher,
    DXNewsFetcher,
    fetch_all_data
)
from models import DXStation
from exceptions import DataStalenessException, DataSourceError
from datetime import timedelta


def _get_default_timezone() -> ZoneInfo:
    try:
        if sys.platform.startswith('win'):
            zone = ZoneInfo("America/New_York")
        elif sys.platform.startswith('darwin'):
            zone = ZoneInfo("America/Los_Angeles")
        else:
            zone = ZoneInfo("Etc/UTC")
        return zone
    except:
        return ZoneInfo("Etc/UTC")


def get_timezone() -> ZoneInfo:
    timezone_file = Path(__file__).parent.parent / "timezone.txt"
    if timezone_file.exists():
        try:
            with open(timezone_file, 'r') as file:
                return ZoneInfo(file.read().strip())
        except Exception as e:
            print(f"Error reading timezone file: {e}")
    return _get_default_timezone()


def _ensure_timezone(dt: datetime, tz: ZoneInfo) -> datetime:
    if dt.tzname() != tz.key:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=tz)
        if dt.tzinfo != tz:
            # Assuming the datetime is already in UTC
            try:
                return dt.astimezone(tz)
            except Exception as e:
                print(f"Error converting timezone: {e}")
    return dt

