"""Unit tests for NG3K iCal parsing and potential-spot extraction."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from src.data_fetchers.ng3k import (
    NG3KFetcher,
    extract_callsigns,
    is_full_call,
    parse_dxcal_ics,
)
from src.models import DXStation


SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Market Reef (OJ0)
DTSTART;VALUE=DATE:20260815
DTEND;VALUE=DATE:20260822
DESCRIPTION:By OH3JR as OJ0JR and OH2YL as OJ0YL fm IOTA EU-053\\; 80-10m\\; CW
 SSB FT8
END:VEVENT
BEGIN:VEVENT
SUMMARY:Franz Josef Land (RI1FJL)
DTSTART;VALUE=DATE:20260815
DTEND;VALUE=DATE:20260829
DESCRIPTION:By R7AL RW8A\\; 160-10m\\; CW SSB
END:VEVENT
BEGIN:VEVENT
SUMMARY:Canary Is (EA8)
DTSTART;VALUE=DATE:20260818
DTEND;VALUE=DATE:20260829
DESCRIPTION:By IZ1GDB as EA8/IZ1GDB fm Mogan\\, Gran Canaria\\; 40 20 15 10m
END:VEVENT
BEGIN:VEVENT
SUMMARY:Mauritius (3B8)
DTSTART;VALUE=DATE:20260821
DTEND;VALUE=DATE:20260827
DESCRIPTION:By SQ9UM as 3B8/SQ9UM\\; 40-10m\\; CW FT8
END:VEVENT
BEGIN:VEVENT
SUMMARY:Lesotho (7P8FR)
DTSTART;VALUE=DATE:20260822
DTEND;VALUE=DATE:20260822
DESCRIPTION:By ZR6FAR\\; 40-10m\\; FT8
END:VEVENT
BEGIN:VEVENT
SUMMARY:St Lucia (J68TT)
DTSTART;VALUE=DATE:20260801
DTEND;VALUE=DATE:20260810
DESCRIPTION:By N4XTT\\; 40-10m
END:VEVENT
END:VCALENDAR
"""


class TestCallsignHelpers:
    @pytest.mark.parametrize(
        "token,expected",
        [
            ("RI1FJL", True),
            ("TF5SS", True),
            ("7P8FR", True),
            ("V47JA", True),
            ("HB040A", True),
            ("3B8/SQ9UM", True),
            ("EA8/IZ1GDB", True),
            ("OJ0JR", True),
            ("EA8", False),
            ("OJ0", False),
            ("3B8", False),
            ("FR", False),
            ("J3", False),
            ("", False),
        ],
    )
    def test_is_full_call(self, token, expected):
        assert is_full_call(token) is expected

    def test_as_calls_preferred_over_prefix_summary(self):
        place, calls = extract_callsigns(
            "Market Reef (OJ0)",
            "By OH3JR as OJ0JR and OH2YL as OJ0YL fm IOTA EU-053",
        )
        assert place == "Market Reef"
        assert calls == ["OJ0JR", "OJ0YL"]

    def test_summary_call_used_when_no_as(self):
        place, calls = extract_callsigns(
            "Franz Josef Land (RI1FJL)",
            "By R7AL RW8A; 160-10m; CW SSB",
        )
        assert place == "Franz Josef Land"
        assert calls == ["RI1FJL"]

    def test_portable_as_call(self):
        place, calls = extract_callsigns(
            "Mauritius (3B8)",
            "By SQ9UM as 3B8/SQ9UM; 40-10m; CW FT8",
        )
        assert place == "Mauritius"
        assert calls == ["3B8/SQ9UM"]

    def test_prefix_only_without_as_is_skipped(self):
        place, calls = extract_callsigns("Canary Is (EA8)", "Holiday style; 20m")
        assert place == "Canary Is"
        assert calls == []


class TestParseDxcal:
    def test_active_today_only(self):
        stations = parse_dxcal_ics(SAMPLE_ICS, today=date(2026, 8, 21))
        calls = {s.callsign for s in stations}
        assert calls == {"OJ0JR", "OJ0YL", "RI1FJL", "EA8/IZ1GDB", "3B8/SQ9UM"}
        assert "7P8FR" not in calls
        assert "J68TT" not in calls
        assert all(s.potential for s in stations)
        assert all(s.source == "NG3K" for s in stations)

    def test_upcoming_same_day_window_included(self):
        stations = parse_dxcal_ics(SAMPLE_ICS, today=date(2026, 8, 22))
        calls = {s.callsign for s in stations}
        assert "7P8FR" in calls
        assert "3B8/SQ9UM" in calls
        # Market Reef's last day is the 22nd (inclusive window)
        assert "OJ0JR" in calls

    def test_day_after_window_excluded(self):
        stations = parse_dxcal_ics(SAMPLE_ICS, today=date(2026, 8, 23))
        calls = {s.callsign for s in stations}
        assert "OJ0JR" not in calls
        assert "7P8FR" not in calls
        assert "3B8/SQ9UM" in calls

    def test_past_operations_excluded(self):
        stations = parse_dxcal_ics(SAMPLE_ICS, today=date(2026, 8, 21))
        assert all(s.callsign != "J68TT" for s in stations)

    def test_country_canonicalized(self):
        stations = parse_dxcal_ics(SAMPLE_ICS, today=date(2026, 8, 21))
        by_call = {s.callsign: s for s in stations}
        assert by_call["RI1FJL"].dx_country == "Franz Josef Land"
        assert by_call["EA8/IZ1GDB"].dx_country == "Canary Islands"
        assert by_call["3B8/SQ9UM"].dx_country == "Mauritius"

    def test_comment_includes_date_range(self):
        stations = parse_dxcal_ics(SAMPLE_ICS, today=date(2026, 8, 21))
        ri = next(s for s in stations if s.callsign == "RI1FJL")
        assert "15 Aug" in ri.comment
        assert "29 Aug" in ri.comment

    def test_empty_calendar(self):
        assert parse_dxcal_ics("BEGIN:VCALENDAR\nEND:VCALENDAR\n", today=date(2026, 8, 21)) == []


class TestNG3KFetcher:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_fetch_parses_ics(self, mock_session, monkeypatch):
        fetcher = NG3KFetcher(mock_session)
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=SAMPLE_ICS)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "src.data_fetchers.ng3k.parse_dxcal_ics",
            lambda text, today=None: parse_dxcal_ics(text, today=date(2026, 8, 21)),
        )

        stations = await fetcher.fetch()
        assert all(isinstance(s, DXStation) for s in stations)
        assert all(s.potential for s in stations)
        assert {s.callsign for s in stations} == {
            "OJ0JR", "OJ0YL", "RI1FJL", "EA8/IZ1GDB", "3B8/SQ9UM",
        }

    @pytest.mark.asyncio
    async def test_fetch_empty_body_returns_empty(self, mock_session):
        fetcher = NG3KFetcher(mock_session)
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="")
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        assert await fetcher.fetch() == []
