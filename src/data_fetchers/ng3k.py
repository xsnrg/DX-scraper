"""NG3K announced-DX calendar → potential spots.

Only operations whose date window includes today, and only when a real
callsign can be extracted. Prefix-only entries (EA8, FR, 3B8, …) are skipped
unless the description names the operating call (`as 3B8/SQ9UM`).
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import List, Optional

import aiohttp

from .base import BaseFetcher
from ..dxcc import DXCC_LOOKUP
from ..models import DXStation
from ..timeutil import utc_now, utc_today

logger = logging.getLogger(__name__)

ICS_URL = "https://www.danplanet.com/dxcal.ics"

# W1AW, TF5SS, V47JA, HB040A  /  7P8FR, 3W9C, 9T0MD
_FULL_CALL = re.compile(
    r"^((?:[A-Z]{1,2}|\d[A-Z]{1,2})\d{1,4}[A-Z]{1,4})$"
)
# Prefix with no suffix letters: EA8, OJ0, 3B8, J3
_PREFIX_ONLY = re.compile(
    r"^((?:[A-Z]{1,2}|\d[A-Z]{1,2})\d{1,4})$"
)
_AS_CALL = re.compile(
    r"\bas\s+([A-Z0-9]{1,3}\d[A-Z0-9]{0,5}(?:/[A-Z0-9]{1,6})?)",
    re.IGNORECASE,
)
_SUMMARY = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")
_BANDS = re.compile(
    r"\b(?:\d+\s*-\s*\d+\s*m|\d+(?:\s+\d+)+\s*m|\d+\s*m|HF|VHF|UHF)\b",
    re.IGNORECASE,
)
# Longer tokens first so FT8/PSK31 win over FT/PSK.
_MODES = (
    "PSK31", "MSK144", "JT65", "JT9", "FT8", "FT4", "JS8",
    "RTTY", "OLIVIA", "MIXED", "WSPR", "Q65",
    "USB", "LSB", "SSB", "CW", "FM", "AM", "PSK",
)


def _unescape(text: str) -> str:
    return (
        text.replace("\\n", " ")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def _unfold(ics: str) -> list[str]:
    lines: list[str] = []
    for raw in ics.splitlines():
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    token = value.split("T")[0].replace("-", "")
    try:
        return datetime.strptime(token[:8], "%Y%m%d").date()
    except ValueError:
        return None


def is_full_call(token: str) -> bool:
    """True if token is a station call, including portable PREFIX/CALL."""
    token = (token or "").upper().strip()
    if not token:
        return False
    if "/" in token:
        left, right = token.split("/", 1)
        # 3B8/SQ9UM — left is a prefix, right is the home call
        if _PREFIX_ONLY.match(left) and _FULL_CALL.match(right):
            return True
        return bool(_FULL_CALL.match(left) or _FULL_CALL.match(right))
    return bool(_FULL_CALL.match(token))


def extract_callsigns(summary: str, description: str) -> tuple[str, list[str]]:
    """Return (place name, operating callsigns) for one calendar event."""
    summary = _unescape(summary or "").strip()
    description = _unescape(description or "")
    match = _SUMMARY.match(summary)
    if match:
        place, token = match.group(1).strip(), match.group(2).strip().upper()
    else:
        place, token = summary, ""

    calls: list[str] = []
    for found in _AS_CALL.finditer(description):
        candidate = found.group(1).upper().rstrip(".,;")
        if is_full_call(candidate) and candidate not in calls:
            calls.append(candidate)
    if token and is_full_call(token) and token not in calls:
        calls.insert(0, token)
    return place, calls


def _extract_bands(text: str) -> list[str]:
    seen: list[str] = []
    for match in _BANDS.finditer(text):
        band = re.sub(r"\s+", " ", match.group(0)).strip()
        if band.lower() not in {b.lower() for b in seen}:
            seen.append(band)
    return seen


def _extract_modes(text: str) -> list[str]:
    known = {mode.upper(): mode for mode in _MODES}
    found: list[str] = []
    for token in re.findall(r"[A-Za-z0-9]+", text):
        # NG3K uses "fm" for "from"; do not treat it as FM.
        if token.lower() in {"fm", "am"} and token not in {"FM", "AM"}:
            continue
        canonical = known.get(token.upper())
        if canonical and canonical not in found:
            found.append(canonical)
    return found


def schedule_fields(description: str) -> tuple[str, str]:
    """Return (band, mode) from an NG3K description. No dates, QSL, or prose."""
    text = _unescape(description or "")
    band = ", ".join(_extract_bands(text))
    mode = " ".join(_extract_modes(text))
    return band, mode


def compact_comment(description: str, calls: list[str] | None = None) -> str:
    """Bands and modes only; callsigns live in the callsign column."""
    band, mode = schedule_fields(description)
    return " · ".join(part for part in (band, mode) if part)



def _canonical_country(place: str) -> str:
    """Map NG3K place names onto DXCC_LOOKUP keys when we can."""
    if not place:
        return ""
    variants = [place]
    if place.endswith(" Is"):
        variants.append(place[:-3] + " Islands")
        variants.append(place[:-3] + " Island")
    if place.endswith(" I"):
        variants.append(place[:-2] + " Island")
        variants.append(place[:-2] + " Islands")
    if place.startswith("St "):
        variants.append("St. " + place[3:])
        variants.append("Saint " + place[3:])
    if place.startswith("Dem Rep "):
        variants.append("Dem. Rep. of the " + place[8:])
    lower = {key.lower(): key for key in DXCC_LOOKUP}
    for variant in variants:
        if variant in DXCC_LOOKUP:
            return variant
        mapped = lower.get(variant.lower())
        if mapped:
            return mapped
    return place


def parse_dxcal_ics(text: str, today: Optional[date] = None) -> List[DXStation]:
    """Parse the NG3K iCal feed into potential spots for operations QRV today."""
    today = today or utc_today()
    events: list[dict] = []
    current: dict[str, str] = {}
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current:
                events.append(current)
            current = {}
        elif ":" in line:
            key, value = line.split(":", 1)
            current[key.split(";")[0]] = value

    now = utc_now()
    stations: list[DXStation] = []
    seen: set[str] = set()
    for event in events:
        start = _parse_date(event.get("DTSTART", ""))
        end = _parse_date(event.get("DTEND", ""))
        if start is None:
            continue
        if end is None:
            end = start
        # NG3K uses date-only events; treat the window as inclusive.
        if not (start <= today <= end):
            continue

        place, calls = extract_callsigns(
            event.get("SUMMARY", ""), event.get("DESCRIPTION", "")
        )
        country = _canonical_country(place)
        band, mode = schedule_fields(event.get("DESCRIPTION", ""))

        for call in calls:
            if call in seen:
                continue
            seen.add(call)
            stations.append(
                DXStation(
                    callsign=call,
                    dx_country=country,
                    band=band,
                    mode=mode,
                    last_update=now,
                    source="NG3K",
                    potential=True,
                )
            )
    return stations


class NG3KFetcher(BaseFetcher):
    def __init__(self, session: aiohttp.ClientSession):
        super().__init__("NG3K", session)
        self.api_url = ICS_URL

    async def fetch(self) -> List[DXStation]:
        ics = await self.fetch_with_retry(self.api_url)
        if not ics:
            return []
        try:
            stations = parse_dxcal_ics(ics)
        except Exception as exc:
            logger.error(f"NG3K: failed to parse calendar: {exc}")
            return []
        logger.info(f"NG3K: {len(stations)} potential spots for today")
        return stations
