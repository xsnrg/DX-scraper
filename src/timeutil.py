"""UTC-only clock for DX-scraper.

Ham-radio spots, DXpedition calendars, QRZ ADIF, and cache file times are all
interpreted and stored as UTC. Naive datetimes are treated as UTC; aware
values in other zones are converted.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

UTC = timezone.utc

_PARSE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y%m%dT%H%M%S",
    "%Y%m%d %H%M%S",
)


def utc_now() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(UTC)


def as_utc(dt: datetime) -> datetime:
    """Return ``dt`` as timezone-aware UTC.

    Naive values are assumed already UTC (cluster feeds often omit the
    offset). Aware values are converted with ``astimezone``.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def utc_today():
    """Calendar date in UTC."""
    return utc_now().date()


def parse_utc(raw: Optional[str], *, fallback_now: bool = True) -> datetime:
    """Parse a timestamp string as UTC.

    Accepts ISO-8601 (including a trailing ``Z``), space-separated
    ``YYYY-MM-DD HH:MM[:SS]``, and a few compact forms used by cluster
    feeds. Invalid or empty input returns ``utc_now()`` when
    ``fallback_now`` is true, otherwise raises ``ValueError``.
    """
    text = (raw or "").strip()
    if not text:
        if fallback_now:
            return utc_now()
        raise ValueError("empty timestamp")

    iso = text.replace("Z", "+00:00").replace("z", "+00:00")
    try:
        return as_utc(datetime.fromisoformat(iso))
    except ValueError:
        pass

    for fmt in _PARSE_FORMATS:
        try:
            return as_utc(datetime.strptime(text, fmt))
        except ValueError:
            continue

    if fallback_now:
        return utc_now()
    raise ValueError(f"unrecognized timestamp: {raw!r}")


def format_utc(dt: datetime, *, timespec: str = "seconds") -> str:
    """Format a datetime as ``YYYY-MM-DD HH:MM[:SS] UTC``."""
    dt = as_utc(dt)
    if timespec == "minutes":
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def format_iso_utc(dt: datetime) -> str:
    """ISO-8601 UTC string with a ``Z`` suffix."""
    text = as_utc(dt).isoformat(timespec="seconds")
    if text.endswith("+00:00"):
        return text[:-6] + "Z"
    return text


def format_mtime_utc(mtime: float) -> str:
    """Format a POSIX mtime (seconds since epoch) as UTC."""
    return format_utc(datetime.fromtimestamp(mtime, tz=UTC))
