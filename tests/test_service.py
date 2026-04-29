import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.models import DXStation
from src.service import DXPeditionService


class TestDXPeditionService:
    @pytest.fixture
    def service(self):
        return DXPeditionService(max_age_seconds=3600)

    @pytest.fixture
    def sample_stations(self):
        now = datetime.now(timezone.utc)
        return [
            DXStation(
                callsign="P49P",
                dx_country="Palau",
                spotter_country="",
                spotter="Test Spotter",
                band="20m",
                frequency=14.2,
                mode="SSB",
                comment="Palau DXpedition",
                last_update=now - timedelta(minutes=5),
                source="DX Summit"
            ),
            DXStation(
                callsign="VK7ZZ",
                dx_country="Tasmania",
                spotter_country="",
                spotter="Test Spotter",
                band="40m",
                frequency=7.1,
                mode="CW",
                comment="Tasmania DXpedition",
                last_update=now - timedelta(minutes=10),
                source="Spothole"
            ),
            DXStation(
                callsign="P49P",
                dx_country="Palau",
                spotter_country="",
                spotter="Test Spotter",
                band="20m",
                frequency=14.2,
                mode="SSB",
                comment="Palau DXpedition (duplicate)",
                last_update=now - timedelta(minutes=2),
                source="DX Summit"
            )
        ]

    def test_filter_by_age(self, service, sample_stations):
        old_station = DXStation(
            callsign="OLD1",
            dx_country="Somewhere",
            spotter="Test Spotter",
            band="",
            last_update=datetime.now(timezone.utc) - timedelta(hours=2),
            source="Test"
        )
        all_stations = sample_stations + [old_station]
        
        filtered = service.filter_by_age(all_stations)
        assert len(filtered) == len(sample_stations)
        assert all(s.last_update >= datetime.now(timezone.utc) - timedelta(seconds=3600) for s in filtered)

    def test_deduplicate_stations(self, service, sample_stations):
        deduped = service.deduplicate_stations(sample_stations)
        assert len(deduped) == 2
        p49p = [s for s in deduped if s.callsign == "P49P"][0]
        assert p49p.last_update == sample_stations[2].last_update

    def test_get_active_bands(self, service, sample_stations):
        active = service.get_active_bands(sample_stations)
        assert len(active) == len(sample_stations)

    def test_get_station_by_callsign(self, service, sample_stations):
        station = service.get_station_by_callsign(sample_stations, "P49P")
        assert station is not None
        assert station.callsign == "P49P"
        
        missing = service.get_station_by_callsign(sample_stations, "ZZZ999")
        assert missing is None

    @pytest.mark.asyncio
    async def test_get_current_data(self, service):
        with patch("src.service.fetch_all_data") as mock_fetch:
            mock_fetch.return_value = [
                DXStation(
                    callsign="TEST1",
                    dx_country="Test Country",
                    spotter="Test Spotter",
                    band="20m",
                    last_update=datetime.now(timezone.utc),
                    source="Test"
                )
            ]
            
            summary = await service.get_current_data()
            assert summary.total_stations == 1
            assert summary.active_stations == 1
            assert len(summary.stations) == 1
            assert summary.stations[0].callsign == "TEST1"

    @pytest.mark.asyncio
    async def test_get_current_data_with_staleness_exception(self, service):
        from src.exceptions import DataStalenessException
        
        with patch("src.service.fetch_all_data") as mock_fetch:
            mock_fetch.side_effect = DataStalenessException(3600, 7200)
            
            with pytest.raises(DataStalenessException):
                await service.get_current_data()

    @pytest.mark.asyncio
    async def test_get_current_data_with_generic_exception(self, service):
        with patch("src.service.fetch_all_data") as mock_fetch:
            mock_fetch.side_effect = Exception("Unexpected error")
            
            with pytest.raises(Exception):
                await service.get_current_data()

    @pytest.mark.asyncio
    async def test_get_current_data_with_max_age_override(self, service):
        with patch("src.service.fetch_all_data") as mock_fetch:
            mock_fetch.return_value = [
                DXStation(
                    callsign="TEST1",
                    dx_country="Test Country",
                    spotter="Test Spotter",
                    band="20m",
                    last_update=datetime.now(timezone.utc),
                    source="Test"
                )
            ]
            
            await service.get_current_data(max_age_seconds=7200)
            assert service.max_age_seconds == 7200

    @pytest.mark.asyncio
    async def test_get_current_data_empty_stations(self, service):
        with patch("src.service.fetch_all_data") as mock_fetch:
            mock_fetch.return_value = []
            
            summary = await service.get_current_data()
            assert summary.total_stations == 0
            assert summary.active_stations == 0
            assert len(summary.stations) == 0
            assert summary.data_sources == []

    @pytest.mark.asyncio
    async def test_get_current_data_with_none_max_age(self, service):
        with patch("src.service.fetch_all_data") as mock_fetch:
            mock_fetch.return_value = [
                DXStation(
                    callsign="TEST1",
                    dx_country="Test Country",
                    spotter="Test Spotter",
                    band="20m",
                    last_update=datetime.now(timezone.utc),
                    source="Test"
                )
            ]
            
            summary = await service.get_current_data(max_age_seconds=None)
            assert summary.total_stations == 1

    def test_filter_by_age_empty_list(self, service):
        filtered = service.filter_by_age([])
        assert filtered == []

    def test_deduplicate_stations_empty_list(self, service):
        deduped = service.deduplicate_stations([])
        assert deduped == []

    def test_deduplicate_stations_all_duplicates(self, service):
        now = datetime.now(timezone.utc)
        duplicate_stations = [
            DXStation(
                callsign="SAME1",
                dx_country="Loc1",
                spotter="Test Spotter",
                band="20m",
                last_update=now - timedelta(minutes=10),
                source="Test"
            ),
            DXStation(
                callsign="SAME1",
                dx_country="Loc1",
                spotter="Test Spotter",
                band="20m",
                comment="Station 1 Updated",
                last_update=now - timedelta(minutes=5),
                source="Test"
            )
        ]
        
        deduped = service.deduplicate_stations(duplicate_stations)
        assert len(deduped) == 1
        assert deduped[0].comment == "Station 1 Updated"

    def test_get_active_bands_empty_list(self, service):
        active = service.get_active_bands([])
        assert active == []

    def test_get_station_by_callsign_empty_list(self, service):
        station = service.get_station_by_callsign([], "P49P")
        assert station is None

    def test_get_station_by_callsign_case_insensitive(self, service, sample_stations):
        station = service.get_station_by_callsign(sample_stations, "p49p")
        assert station is not None
        assert station.callsign == "P49P"
        
        station = service.get_station_by_callsign(sample_stations, "vk7zz")
        assert station is not None
        assert station.callsign == "VK7ZZ"

    def test_get_station_by_callsign_partial_match(self, service, sample_stations):
        station = service.get_station_by_callsign(sample_stations, "P49")
        assert station is None
