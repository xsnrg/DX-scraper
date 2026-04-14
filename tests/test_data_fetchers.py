import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from src.data_fetchers import (
    BaseFetcher,
    DXSummitFetcher,
    DXClusterFetcher,
    HamQSLFetcher,
    DXNewsFetcher,
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
        
        with pytest.raises(DataStalenessException):
            base_fetcher.validate_age(last_update)


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
        assert stations[0].name == "Test Station"
        assert stations[0].location == ""
        assert "20m" in stations[0].bands
        assert stations[0].active_band == "20m"
        assert stations[0].active_mode == "CW"
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
        assert len(stations) == 0

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
        html_content = """
        <html>
            <tr>
                <td>XY9ZZ</td>
                <td>Cluster Station</td>
                <td>Canada</td>
                <td>2025-01-09 10:30 11:00</td>
            </tr>
        </html>
        """
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html_content)
        
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()

        assert len(stations) == 1
        assert stations[0].callsign == "XY9ZZ"
        assert stations[0].source == "DX Cluster"
        assert stations[0].status == "active"
        assert stations[0].bands == []
        assert stations[0].active_band is None

    @pytest.mark.asyncio
    async def test_fetch_skips_comments(self, fetcher, mock_session):
        html_content = """
        <html>
            <tr>
                <td>#COMMENT</td>
                <td>Comment</td>
                <td>World</td>
                <td>2025-01-09 10:30 11:00</td>
            </tr>
            <tr>
                <td>XY9ZZ</td>
                <td>Real Station</td>
                <td>Canada</td>
                <td>2025-01-09 10:30 11:00</td>
            </tr>
        </html>
        """
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html_content)
        
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()
        assert len(stations) == 1
        assert stations[0].callsign == "XY9ZZ"


class TestHamQSLFetcher:
    @pytest.fixture
    def mock_session(self):
        return MagicMock(spec=aiohttp.ClientSession)

    @pytest.fixture
    def fetcher(self, mock_session):
        return HamQSLFetcher(mock_session)

    @pytest.mark.asyncio
    async def test_fetch_successful(self, fetcher, mock_session):
        html_content = """
        <html>
            <tr>
                <td>K1ABC</td>
                <td>QSL Station</td>
                <td>USA</td>
                <td>2025-01-09 10:30 12:00</td>
            </tr>
        </html>
        """
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html_content)
        
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        stations = await fetcher.fetch()

        assert len(stations) == 1
        assert stations[0].callsign == "K1ABC"
        assert stations[0].source == "HamQSL"
        assert stations[0].status == "active"


class TestFetchAllData:
    @pytest.mark.asyncio
    async def test_fetch_all_data_success(self, mocker):
        mock_fetcher = MagicMock()
        mock_fetcher.name = "Test Fetcher"
        mock_fetcher.fetch = AsyncMock(return_value=[
            DXStation(
                callsign="AB1CD",
                name="Test",
                location="USA",
                last_update=datetime.now(timezone.utc),
                source="Test"
            )
        ])
        
        mocker.patch('src.data_fetchers.DXSummitFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.DXClusterFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.HamQSLFetcher', return_value=mock_fetcher)
        mocker.patch('src.data_fetchers.DXNewsFetcher', return_value=mock_fetcher)
        
        with patch('src.data_fetchers.Config.DATA_SOURCES', {
            "dx_summit": {"enabled": True},
            "dxcluster": {"enabled": True},
            "hamqsl": {"enabled": True},
            "dxnews": {"enabled": True}
        }):
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
                
                stations = await fetch_all_data()

                assert len(stations) == 4
                assert all(s.source == "Test" for s in stations)

    @pytest.mark.asyncio
    async def test_fetch_all_data_with_errors(self, mocker):
        mock_fetcher = MagicMock()
        mock_fetcher.name = "Failing Fetcher"
        mock_fetcher.fetch = AsyncMock(side_effect=Exception("Fetch failed"))
        
        mocker.patch('src.data_fetchers.DXSummitFetcher', return_value=mock_fetcher)
        
        with patch('src.data_fetchers.Config.DATA_SOURCES', {
            "dx_summit": {"enabled": True},
            "dxcluster": {"enabled": False},
            "hamqsl": {"enabled": False},
            "dxnews": {"enabled": False}
        }):
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
                
                stations = await fetch_all_data()
                
                assert len(stations) == 0

    @pytest.mark.asyncio
    async def test_fetch_all_data_disabled_sources(self, mocker):
        mocker.patch('src.data_fetchers.Config.DATA_SOURCES', {
            "dx_summit": {"enabled": False},
            "dxcluster": {"enabled": False},
            "hamqsl": {"enabled": False},
            "dxnews": {"enabled": False}
        })
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            stations = await fetch_all_data()
            
            assert len(stations) == 0