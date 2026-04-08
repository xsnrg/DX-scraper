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
                name="Palau DXpedition",
                location="Palau",
                bands=["20m", "15m", "10m"],
                active_band="20m",
                active_mode="SSB",
                last_update=now - timedelta(minutes=5),
                source="DX Summit"
            ),
            DXStation(
                callsign="VK7ZZ",
                name="Tasmania DXpedition",
                location="Tasmania",
                bands=["40m", "20m", "15m"],
                active_band="40m",
                active_mode="CW",
                last_update=now - timedelta(minutes=10),
                source="DX Cluster"
            ),
            DXStation(
                callsign="P49P",
                name="Palau DXpedition (duplicate)",
                location="Palau",
                bands=["20m", "15m"],
                active_band="20m",
                active_mode="SSB",
                last_update=now - timedelta(minutes=2),
                source="DX Summit"
            )
        ]

    def test_filter_by_age(self, service, sample_stations):
        old_station = DXStation(
            callsign="OLD1",
            name="Old Station",
            location="Somewhere",
            bands=[],
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
                    name="Test Station 1",
                    location="Test",
                    bands=["20m"],
                    last_update=datetime.now(timezone.utc),
                    source="Test"
                )
            ]
            
            summary = await service.get_current_data()
            assert summary.total_stations == 1
            assert summary.active_stations == 1
            assert len(summary.stations) == 1
            assert summary.stations[0].callsign == "TEST1"
