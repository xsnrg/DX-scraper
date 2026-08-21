import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from src.data_fetchers import (
    BaseFetcher,
    DXSummitFetcher,
    DXClusterFetcher,
    DXNewsFetcher,
    PotaFetcher,
    HamQTHFetcher,
    fetch_all_data
)
from src.models import DXStation
from src.exceptions import DataStalenessException, DataSourceError


class TestBaseFetcher:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def base_fetcher(self, mock_session):
        return BaseFetcher("TestFetcher", mock_session)

    @pytest.mark.asyncio
    async def test_fetch_with_retry_success(self, mock_session, base_fetcher):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html></html>")

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await base_fetcher.fetch_with_retry("http://test.com")

        assert result == "<html></html>"
        mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_with_retry_timeout(self, mock_session, base_fetcher):
        mock_session.get.side_effect = asyncio.TimeoutError("Timeout")

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(DataSourceError):
                await base_fetcher.fetch_with_retry("http://test.com")

    @pytest.mark.asyncio
    async def test_validate_age_valid(self, base_fetcher):
        last_update = datetime.now(timezone.utc) - timedelta(seconds=100)
        assert base_fetcher.validate_age(last_update) is True

    @pytest.mark.asyncio
    async def test_validate_age_stale(self, base_fetcher):
        last_update = datetime.now(timezone.utc) - timedelta(seconds=7200)

        assert base_fetcher.validate_age(last_update) is False

    def test_validate_age_naive_datetime_treated_as_utc(self, base_fetcher):
        last_update = datetime.now() - timedelta(seconds=100)
        assert last_update.tzinfo is None
        assert base_fetcher.validate_age(last_update) is True

    def test_validate_all_stations_empty_raises(self, base_fetcher):
        with pytest.raises(DataStalenessException) as exc:
            base_fetcher.validate_all_stations([])
        assert exc.value.actual_age == 0

    @pytest.mark.asyncio
    async def test_fetch_with_retry_http_error_then_success(self, mock_session, base_fetcher):
        fail = AsyncMock()
        fail.status = 500
        fail.text = AsyncMock(return_value="err")
        ok = AsyncMock()
        ok.status = 200
        ok.text = AsyncMock(return_value="ok")

        mock_session.get.side_effect = [
            MagicMock(__aenter__=AsyncMock(return_value=fail), __aexit__=AsyncMock(return_value=None)),
            MagicMock(__aenter__=AsyncMock(return_value=ok), __aexit__=AsyncMock(return_value=None)),
        ]
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await base_fetcher.fetch_with_retry("http://test.com")
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_fetch_with_retry_http_errors_exhausted(self, mock_session, base_fetcher):
        fail = AsyncMock()
        fail.status = 503
        fail.text = AsyncMock(return_value="err")
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=fail)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(DataSourceError) as exc:
                await base_fetcher.fetch_with_retry("http://test.com")
        assert exc.value.source == "TestFetcher"

    @pytest.mark.asyncio
    async def test_fetch_with_retry_generic_exception_then_success(self, mock_session, base_fetcher):
        ok = AsyncMock()
        ok.status = 200
        ok.text = AsyncMock(return_value="recovered")
        mock_session.get.side_effect = [
            RuntimeError("connection reset"),
            MagicMock(__aenter__=AsyncMock(return_value=ok), __aexit__=AsyncMock(return_value=None)),
        ]
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await base_fetcher.fetch_with_retry("http://test.com")
        assert result == "recovered"


class TestDXSummitFetcher:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def fetcher(self, mock_session):
        return DXSummitFetcher(mock_session)

    def _csv(self, rows):
        header = "id,de_call,dx_call,info,frequency,time,dx_country,de_latitude,de_longitude,dx_latitude,dx_longitude"
        return header + "\n" + "\n".join(rows)

    @pytest.mark.asyncio
    async def test_fetch_successful(self, fetcher, mock_session):
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
        csv_content = self._csv([
            f"1,SPOTTER1,AB1CD,CW Test Station,14200,{timestamp},United States,0,0,0,0",
        ])
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=csv_content)

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()

        assert len(stations) == 1
        assert stations[0].callsign == "AB1CD"
        assert stations[0].dx_country == "United States"
        assert stations[0].band == "20m"
        assert stations[0].mode == "CW"
        assert stations[0].frequency == pytest.approx(14.2)
        assert stations[0].spotter == "SPOTTER1"
        assert stations[0].source == "DX Summit"
        assert stations[0].status == "active"
        assert stations[0].last_update.tzinfo is not None

    @pytest.mark.asyncio
    async def test_fetch_stale_data_is_kept(self, fetcher, mock_session):
        """DX Summit does not filter by age; stale spots are returned."""
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=7200)
        timestamp = stale_time.strftime("%Y-%m-%dT%H:%M:%S")
        csv_content = self._csv([
            f"1,SPOTTER1,AB1CD,Test Station,14200,{timestamp},United States,0,0,0,0",
        ])
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=csv_content)

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert stations[0].callsign == "AB1CD"

    @pytest.mark.asyncio
    async def test_fetch_invalid_date_uses_now(self, fetcher, mock_session):
        csv_content = self._csv([
            "1,SPOTTER1,AB1CD,Test Station,14200,invalid-date,United States,0,0,0,0",
        ])
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=csv_content)

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert abs((datetime.now(timezone.utc) - stations[0].last_update).total_seconds()) < 2
        assert stations[0].last_update.tzinfo is not None

    @pytest.mark.asyncio
    async def test_fetch_parses_mode_from_info(self, fetcher, mock_session):
        csv_content = self._csv([
            "1,HZ1ES,4L1BB,FT8 1462hz tnx,7074.0,2026-08-21T03:38:58,United States,0,0,0,0",
        ])
        _mock_get(mock_session, csv_content)
        stations = await fetcher.fetch()
        assert stations[0].mode == "FT8"
        assert stations[0].band == "40m"
        assert stations[0].frequency == pytest.approx(7.074)
        assert stations[0].spotter == "HZ1ES"
        assert stations[0].comment.startswith("FT8")

    @pytest.mark.asyncio
    async def test_naive_timestamp_is_utc(self, fetcher, mock_session):
        csv_content = self._csv([
            "1,DE1AA,W1AW,CQ,14205.0,2026-08-21T03:41:15,United States,0,0,0,0",
        ])
        _mock_get(mock_session, csv_content)
        stations = await fetcher.fetch()
        assert stations[0].last_update.tzinfo == timezone.utc
        assert stations[0].last_update.hour == 3
        assert stations[0].last_update.minute == 41


class TestDXClusterFetcher:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def fetcher(self, mock_session):
        return DXClusterFetcher(mock_session)

    @pytest.mark.asyncio
    async def test_fetch_successful(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [{
            "dx_call": "XY9ZZ",
            "dx_country": "Canada",
            "de_call": "Cluster Station",
            "band": "20m",
            "mode": "CW",
            "freq": 14200000,
            "comment": "Test Spot",
            "time_iso": now.isoformat()
        }]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()

        assert len(stations) == 1
        assert stations[0].callsign == "XY9ZZ"
        assert stations[0].source == "Spothole"
        assert stations[0].status == "active"
        assert stations[0].band == "20m"

    @pytest.mark.asyncio
    async def test_fetch_skips_comments(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [
            {
                "dx_call": "#COMMENT",
                "dx_country": "World",
                "de_call": "Comment",
                "band": "20m",
                "mode": "CW",
                "freq": 14200000,
                "comment": "Comment Spot",
                "time_iso": now.isoformat()
            },
            {
                "dx_call": "XY9ZZ",
                "dx_country": "Canada",
                "de_call": "Real Station",
                "band": "20m",
                "mode": "CW",
                "freq": 14200000,
                "comment": "Real Spot",
                "time_iso": now.isoformat()
            }
        ]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert stations[0].callsign == "XY9ZZ"


    @pytest.mark.asyncio
    async def test_fetch_skips_empty_callsign(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [
            {"dx_call": "  ", "band": "20m", "freq": 14200000, "time_iso": now.isoformat()},
            {"dx_call": "W1AW", "band": "20m", "freq": 14200000, "time_iso": now.isoformat()},
        ]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        stations = await fetcher.fetch()
        assert [s.callsign for s in stations] == ["W1AW"]

    @pytest.mark.asyncio
    async def test_fetch_duplicate_keeps_first(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [
            {"dx_call": "W1AW", "band": "20m", "freq": 14200000, "comment": "first", "time_iso": now.isoformat()},
            {"dx_call": "W1AW", "band": "40m", "freq": 7074000, "comment": "second", "time_iso": now.isoformat()},
        ]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert stations[0].band == "20m"
        assert stations[0].comment == "first"

    @pytest.mark.asyncio
    async def test_fetch_converts_hz_to_mhz(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [{"dx_call": "W1AW", "band": "20m", "freq": 14074000, "time_iso": now.isoformat()}]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        stations = await fetcher.fetch()
        assert stations[0].frequency == pytest.approx(14.074)

    @pytest.mark.asyncio
    async def test_fetch_skips_no_band_and_no_frequency(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [{"dx_call": "W1AW", "band": "", "freq": None, "time_iso": now.isoformat()}]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        with pytest.raises(DataStalenessException):
            await fetcher.fetch()

    @pytest.mark.asyncio
    async def test_fetch_skips_stale_spots(self, fetcher, mock_session):
        import json
        stale = datetime.now(timezone.utc) - timedelta(seconds=7200)
        spots = [{"dx_call": "W1AW", "band": "20m", "freq": 14200000, "time_iso": stale.isoformat()}]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        with pytest.raises(DataStalenessException):
            await fetcher.fetch()


class TestFetchAllData:
    @pytest.mark.asyncio
    async def test_fetch_all_data_success(self, mocker):
        mock_fetcher = MagicMock()
        mock_fetcher.name = "Test Fetcher"
        mock_fetcher.fetch = AsyncMock(return_value=[
            DXStation(
                callsign="AB1CD",
                dx_country="USA",
                spotter="Test Spotter",
                band="20m",
                last_update=datetime.now(timezone.utc),
                source="Test"
            )
        ])

        mocker.patch('src.data_fetchers.DXSummitFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.DXClusterFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.DXNewsFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.HamQTHFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.PotaFetcher', return_value=mock_fetcher)

        with patch('src.data_fetchers.Config.DATA_SOURCES', {
            "dx_summit": {"enabled": True},
            "dx_cluster": {"enabled": True},
            "dx_news": {"enabled": True},
            "hamqth": {"enabled": True},
            "pota": {"enabled": True}
        }):
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

                stations = await fetch_all_data(mock_session)

                assert len(stations) == 5
                assert all(s.source == "Test" for s in stations)

    @pytest.mark.asyncio
    async def test_fetch_all_data_with_errors(self, mocker):
        mock_fetcher = MagicMock()
        mock_fetcher.name = "Failing Fetcher"
        mock_fetcher.fetch = AsyncMock(side_effect=Exception("Fetch failed"))

        mocker.patch('src.data_fetchers.DXSummitFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.DXClusterFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.DXNewsFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.HamQTHFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.PotaFetcher', return_value=mock_fetcher)

        with patch('src.data_fetchers.Config.DATA_SOURCES', {
            "dx_summit": {"enabled": True},
            "dx_cluster": {"enabled": False},
            "dx_news": {"enabled": False},
            "hamqth": {"enabled": False},
            "pota": {"enabled": False}
        }):
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

                stations = await fetch_all_data(mock_session)

            assert len(stations) == 0


class TestPotaFetcher:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def fetcher(self, mock_session):
        return PotaFetcher(mock_session)

    @pytest.mark.asyncio
    async def test_fetch_successful(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [{
            "spotId": 50005646,
            "spotTime": now.isoformat(),
            "activator": "W2QMI",
            "frequency": "14286.0",
            "mode": "SSB",
            "reference": "US-6544",
            "spotter": "W2QMI",
            "source": "Web",
            "comments": "QRT THX 73 gone hunting!",
            "name": "New Jersey Coastal State Trail",
            "locationDesc": "US-NJ"
        }]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()

        assert len(stations) == 1
        assert stations[0].callsign == "W2QMI"
        assert stations[0].dx_country == "US-NJ, US-6544"
        assert stations[0].frequency == 14.286
        assert stations[0].mode == "SSB"
        assert stations[0].comment == "QRT THX 73 gone hunting!"
        assert stations[0].source == "POTA"
        assert stations[0].pota_reference == "US-6544"
        assert stations[0].status == "active"

    @pytest.mark.asyncio
    async def test_fetch_skips_no_location(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [{
            "spotId": 1,
            "spotTime": now.isoformat(),
            "activator": "AB1CD",
            "frequency": "7050.0",
            "mode": "CW",
            "reference": "",
            "spotter": "SPOTTER",
            "comments": "",
            "name": "",
            "locationDesc": ""
        }]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 0

    @pytest.mark.asyncio
    async def test_fetch_skips_empty_activator(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [{
            "spotId": 1,
            "spotTime": now.isoformat(),
            "activator": "",
            "frequency": "7050.0",
            "mode": "CW",
            "reference": "US-1",
            "spotter": "SPOTTER",
            "comments": "",
            "name": "",
            "locationDesc": "US-NY"
        }]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 0

    @pytest.mark.asyncio
    async def test_fetch_stale_data_skipped(self, fetcher, mock_session):
        import json
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=7200)
        spots = [{
            "spotId": 1,
            "spotTime": stale_time.isoformat(),
            "activator": "AB1CD",
            "frequency": "7050.0",
            "mode": "CW",
            "reference": "US-1",
            "spotter": "SPOTTER",
            "comments": "",
            "name": "",
            "locationDesc": "US-NY"
        }]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 0

    @pytest.mark.asyncio
    async def test_fetch_only_reference_no_location_desc(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [{
            "spotId": 1,
            "spotTime": now.isoformat(),
            "activator": "AB1CD",
            "frequency": "14200.0",
            "mode": "SSB",
            "reference": "WWFF-123",
            "spotter": "SPOTTER",
            "comments": "",
            "name": "",
            "locationDesc": ""
        }]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert stations[0].dx_country == "WWFF-123"
        assert stations[0].pota_reference == "WWFF-123"

    @pytest.mark.asyncio
    async def test_fetch_only_location_desc_no_reference(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [{
            "spotId": 1,
            "spotTime": now.isoformat(),
            "activator": "AB1CD",
            "frequency": "14200.0",
            "mode": "SSB",
            "reference": "",
            "spotter": "SPOTTER",
            "comments": "",
            "name": "",
            "locationDesc": "US-CA"
        }]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert stations[0].dx_country == "US-CA"
        assert stations[0].pota_reference == ""

    @pytest.mark.asyncio
    async def test_fetch_combined_mode_and_comments(self, fetcher, mock_session):
        import json
        now = datetime.now(timezone.utc)
        spots = [{
            "spotId": 1,
            "spotTime": now.isoformat(),
            "activator": "AB1CD",
            "frequency": "14200.0",
            "mode": "FT8",
            "reference": "WWFF-1",
            "spotter": "SPOTTER",
            "comments": "S59",
            "name": "",
            "locationDesc": "US-TX"
        }]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=json.dumps(spots))

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert stations[0].mode == "FT8"
        assert stations[0].comment == "S59"

    @pytest.mark.asyncio
    async def test_fetch_all_data_disabled_sources(self, mocker):
        mocker.patch('src.data_fetchers.Config.DATA_SOURCES', {
            "dx_summit": {"enabled": False},
            "dx_cluster": {"enabled": False},
            "dx_news": {"enabled": False},
            "hamqth": {"enabled": False},
            "pota": {"enabled": False}
        })

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)

            stations = await fetch_all_data(mock_session)

            assert len(stations) == 0


def _mock_get(session, body):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=body)
    session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
    session.get.return_value.__aexit__ = AsyncMock(return_value=None)


class TestHamQTHFetcher:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def fetcher(self, mock_session):
        return HamQTHFetcher(mock_session)

    @pytest.mark.asyncio
    async def test_fetch_parses_caret_csv(self, fetcher, mock_session):
        line = "K1AR^14074.0^W1AW^CQ DX^1430 2024-01-15^Y^Y^NA^20M^United States^291"
        _mock_get(mock_session, line)
        stations = await fetcher.fetch()
        assert len(stations) == 1
        s = stations[0]
        assert s.callsign == "W1AW"
        assert s.spotter == "K1AR"
        assert s.frequency == pytest.approx(14.074)
        assert s.band == "20M"
        assert s.dx_country == "United States"
        assert s.dxcc == "291"
        assert s.comment == "CQ DX"
        assert s.source == "HamQTH"
        assert s.last_update == datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_fetch_skips_short_lines(self, fetcher, mock_session):
        _mock_get(mock_session, "too^few^fields\n")
        stations = await fetcher.fetch()
        assert stations == []

    @pytest.mark.asyncio
    async def test_fetch_skips_empty_callsign(self, fetcher, mock_session):
        line = "K1AR^14074.0^^CQ DX^1430 2024-01-15^Y^Y^NA^20M^United States^291"
        _mock_get(mock_session, line)
        stations = await fetcher.fetch()
        assert stations == []

    @pytest.mark.asyncio
    async def test_fetch_missing_adif_column(self, fetcher, mock_session):
        line = "K1AR^14074.0^W1AW^CQ^1430 2024-01-15^Y^Y^NA^20M^United States"
        _mock_get(mock_session, line)
        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert stations[0].dxcc == ""

    @pytest.mark.asyncio
    async def test_fetch_empty_frequency_is_none(self, fetcher, mock_session):
        line = "K1AR^^W1AW^CQ^1430 2024-01-15^Y^Y^NA^20M^United States^291"
        _mock_get(mock_session, line)
        stations = await fetcher.fetch()
        assert stations[0].frequency is None

    @pytest.mark.asyncio
    async def test_fetch_bad_date_uses_now(self, fetcher, mock_session):
        line = "K1AR^14074.0^W1AW^CQ^not-a-date^Y^Y^NA^20M^United States^291"
        _mock_get(mock_session, line)
        stations = await fetcher.fetch()
        assert abs((datetime.now(timezone.utc) - stations[0].last_update).total_seconds()) < 2


class TestDXNewsFetcher:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def fetcher(self, mock_session):
        return DXNewsFetcher(mock_session)

    @pytest.mark.asyncio
    async def test_fetch_parses_rss_title(self, fetcher, mock_session):
        rss = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <title>DX News</title>
          <item>
            <title>P49P Palau. From DXNews.com</title>
            <description>DXpedition to Palau</description>
            <pubDate>Mon, 15 Jan 2024 14:30:00 GMT</pubDate>
          </item>
        </channel></rss>
        """
        _mock_get(mock_session, rss)
        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert stations[0].callsign == "P49P"
        assert stations[0].source == "DXNews"
        assert "DXpedition to Palau" in stations[0].comment
        assert stations[0].last_update == datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_fetch_skips_empty_title(self, fetcher, mock_session):
        rss = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item><title>   </title><description>x</description></item>
        </channel></rss>
        """
        _mock_get(mock_session, rss)
        stations = await fetcher.fetch()
        assert stations == []

    @pytest.mark.asyncio
    async def test_fetch_malformed_xml_returns_empty(self, fetcher, mock_session):
        _mock_get(mock_session, "not xml at all <<<")
        stations = await fetcher.fetch()
        assert stations == []

    @pytest.mark.asyncio
    async def test_fetch_empty_body_returns_empty(self, fetcher, mock_session):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="")
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        stations = await fetcher.fetch()
        assert stations == []


class TestFetchAllDataExclude:
    @pytest.mark.asyncio
    async def test_excluded_sources_not_constructed(self, mocker):
        constructed = []

        def make_ctor(name):
            def ctor(session):
                constructed.append(name)
                m = MagicMock()
                m.name = name
                m.fetch = AsyncMock(return_value=[])
                return m
            return ctor

        mocker.patch("src.data_fetchers.DXSummitFetcher", make_ctor("dx_summit"))
        mocker.patch("src.data_fetchers.DXClusterFetcher", make_ctor("dx_cluster"))
        mocker.patch("src.data_fetchers.DXNewsFetcher", make_ctor("dx_news"))
        mocker.patch("src.data_fetchers.HamQTHFetcher", make_ctor("hamqth"))
        mocker.patch("src.data_fetchers.PotaFetcher", make_ctor("pota"))

        session = MagicMock()
        await fetch_all_data(session, excluded_sources=["pota", "DX_NEWS"])
        assert "pota" not in constructed
        assert "dx_news" not in constructed
        assert "dx_summit" in constructed
        assert "dx_cluster" in constructed
        assert "hamqth" in constructed

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self, mocker):
        good = MagicMock()
        good.name = "DX Summit"
        good.fetch = AsyncMock(return_value=[
            DXStation(
                callsign="W1AW",
                source="DX Summit",
                last_update=datetime.now(timezone.utc),
            )
        ])
        bad = MagicMock()
        bad.name = "POTA"
        bad.fetch = AsyncMock(side_effect=Exception("down"))

        mocker.patch("src.data_fetchers.DXSummitFetcher", return_value=good)
        mocker.patch("src.data_fetchers.DXClusterFetcher", return_value=bad)
        mocker.patch("src.data_fetchers.DXNewsFetcher", return_value=bad)
        mocker.patch("src.data_fetchers.HamQTHFetcher", return_value=bad)
        mocker.patch("src.data_fetchers.PotaFetcher", return_value=bad)

        session = MagicMock()
        stations = await fetch_all_data(session)
        assert len(stations) == 1
        assert stations[0].callsign == "W1AW"


class TestDXSummitEdgeCases:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def fetcher(self, mock_session):
        return DXSummitFetcher(mock_session)

    def _csv(self, rows):
        header = "id,de_call,dx_call,info,frequency,time,dx_country,de_latitude,de_longitude,dx_latitude,dx_longitude"
        return header + "\n" + "\n".join(rows)

    @pytest.mark.asyncio
    async def test_empty_dx_call_skipped(self, fetcher, mock_session):
        csv_content = self._csv([
            "1,W1AW,,x,14200,2024-01-15T12:00:00,United States,0,0,0,0",
        ])
        _mock_get(mock_session, csv_content)
        stations = await fetcher.fetch()
        assert stations == []

    @pytest.mark.asyncio
    async def test_duplicate_keeps_first(self, fetcher, mock_session):
        csv_content = self._csv([
            "1,A,W1AW,first,14200,2024-01-15T12:00:00,United States,0,0,0,0",
            "2,B,W1AW,second,7100,2024-01-15T12:00:00,United States,0,0,0,0",
        ])
        _mock_get(mock_session, csv_content)
        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert stations[0].band == "20m"
        assert stations[0].comment == "first"
        assert stations[0].spotter == "A"

    def test_parse_spots_csv_reads_headers(self, fetcher):
        rows = fetcher._parse_spots_csv("dx_call,frequency\nW1AW,14200\n")
        assert rows[0]["dx_call"] == "W1AW"
        assert rows[0]["frequency"] == "14200"

    @pytest.mark.asyncio
    async def test_spotter_falls_back_to_spotter_column(self, fetcher, mock_session):
        csv_content = (
            "dx_call,dx_country,info,frequency,time,spotter\n"
            "W1AW,United States,CQ,14200,2024-01-15T12:00:00Z,K1AR\n"
        )
        _mock_get(mock_session, csv_content)
        stations = await fetcher.fetch()
        assert stations[0].spotter == "K1AR"
