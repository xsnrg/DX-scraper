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


class TestDXSummitFetcher:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def fetcher(self, mock_session):
        return DXSummitFetcher(mock_session)

    @pytest.mark.asyncio
    async def test_fetch_successful(self, fetcher, mock_session):
        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        csv_content = "dx_call,op_name,op_country,info,band,mode,frequency,tx_power,time,spotter_call,spotter_op_name,spotter_op_country,spotter_info,spotter_band,spotter_mode,spotter_frequency,spotter_tx_power,spotter_time,spotter_info\n" + f"AB1CD,Test Op,,Test Station,20m,CW,14200000,100,{timestamp},SPOTTER1,,,,,,"
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=csv_content)

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()

        assert len(stations) == 1
        assert stations[0].callsign == "AB1CD"
        assert stations[0].dx_country == ""
        assert stations[0].band == "20m"
        assert stations[0].mode == "CW"
        assert stations[0].source == "DX Summit"
        assert stations[0].status == "active"

    @pytest.mark.asyncio
    async def test_fetch_stale_data_skipped(self, fetcher, mock_session):
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=7200)
        timestamp = stale_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        csv_content = "dx_call,op_name,op_country,info,band,mode,frequency,tx_power,time,spotter_call,spotter_op_name,spotter_op_country,spotter_info,spotter_band,spotter_mode,spotter_frequency,spotter_tx_power,spotter_time,spotter_info\n" + f"AB1CD,Test Op,,Test Station,20m,CW,14200000,100,{timestamp},SPOTTER1,,,,,,"
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
        csv_content = "dx_call,op_name,op_country,info,band,mode,frequency,tx_power,time,spotter_call,spotter_op_name,spotter_op_country,spotter_info,spotter_band,spotter_mode,spotter_frequency,spotter_tx_power,spotter_time,spotter_info\nAB1CD,Test Op,,Test Station,20m,CW,14200000,100,invalid-date,SPOTTER1,,,,,,"
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=csv_content)

        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert abs((datetime.now(timezone.utc) - stations[0].last_update).total_seconds()) < 1


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
        assert stations[0].frequency == 14286.0
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
