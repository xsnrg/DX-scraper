import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from src.models import DXStation
from src.service import DXPeditionService


@pytest.fixture
def service():
    return DXPeditionService(max_age_seconds=3600)


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


class TestNormalizeBands:
    def test_fills_band_from_frequency(self, service):
        stations = [
            DXStation(
                callsign="W1AW",
                source="DX Summit",
                band="",
                frequency=14.074,
                last_update=datetime.now(timezone.utc),
            )
        ]
        result = service.normalize_bands(stations)
        assert result[0].band == "20m"

    def test_leaves_existing_band_unchanged(self, service):
        stations = [
            DXStation(
                callsign="W1AW",
                source="DX Summit",
                band="40m",
                frequency=14.074,
                last_update=datetime.now(timezone.utc),
            )
        ]
        result = service.normalize_bands(stations)
        assert result[0].band == "40m"

    def test_unknown_frequency_leaves_band_empty(self, service):
        stations = [
            DXStation(
                callsign="W1AW",
                source="DX Summit",
                band="",
                frequency=12.000,
                last_update=datetime.now(timezone.utc),
            )
        ]
        result = service.normalize_bands(stations)
        assert result[0].band == ""

    def test_none_frequency_leaves_band_empty(self, service):
        stations = [
            DXStation(
                callsign="W1AW",
                source="DX Summit",
                band="",
                frequency=None,
                last_update=datetime.now(timezone.utc),
            )
        ]
        result = service.normalize_bands(stations)
        assert result[0].band == ""


class TestResolveDxccNumbers:
    def test_skips_pota_stations(self, service):
        stations = [
            DXStation(
                callsign="W1AW",
                source="POTA",
                dx_country="United States",
                dxcc="",
                last_update=datetime.now(timezone.utc),
            )
        ]
        result = service.resolve_dxcc_numbers(stations)
        assert result[0].dxcc == ""

    def test_strips_leading_zeros(self, service):
        stations = [
            DXStation(
                callsign="W1AW",
                source="DX Summit",
                dxcc="0291",
                last_update=datetime.now(timezone.utc),
            )
        ]
        result = service.resolve_dxcc_numbers(stations)
        assert result[0].dxcc == "291"

    def test_lookup_from_country_when_dxcc_empty(self, service):
        stations = [
            DXStation(
                callsign="JA1ABC",
                source="HamQTH",
                dx_country="Japan",
                dxcc="",
                last_update=datetime.now(timezone.utc),
            )
        ]
        result = service.resolve_dxcc_numbers(stations)
        assert result[0].dxcc == "339"

    def test_unknown_country_becomes_empty(self, service):
        stations = [
            DXStation(
                callsign="XX1XX",
                source="DX Summit",
                dx_country="USA",
                dxcc="",
                last_update=datetime.now(timezone.utc),
            )
        ]
        result = service.resolve_dxcc_numbers(stations)
        assert result[0].dxcc == ""


class TestDedupPotaPriority:
    def test_pota_replaces_non_pota_even_if_older(self, service):
        now = datetime.now(timezone.utc)
        stations = [
            DXStation(
                callsign="W1AW",
                source="DX Summit",
                last_update=now,
                comment="cluster",
            ),
            DXStation(
                callsign="W1AW",
                source="POTA",
                last_update=now - timedelta(minutes=30),
                pota_reference="US-1",
                comment="pota",
            ),
        ]
        result = service.deduplicate_stations(stations)
        assert len(result) == 1
        assert result[0].source == "POTA"
        assert result[0].pota_reference == "US-1"
        assert result[0].sources == ["DX Summit", "POTA"]

    def test_sources_union_is_sorted(self, service):
        now = datetime.now(timezone.utc)
        stations = [
            DXStation(callsign="W1AW", source="Spothole", last_update=now),
            DXStation(callsign="W1AW", source="DX Summit", last_update=now),
            DXStation(callsign="W1AW", source="HamQTH", last_update=now),
        ]
        result = service.deduplicate_stations(stations)
        assert result[0].sources == ["DX Summit", "HamQTH", "Spothole"]


class TestPotentialSpotDedupAndAge:
    def test_live_spot_replaces_potential(self, service):
        now = datetime.now(timezone.utc)
        stations = [
            DXStation(
                callsign="RI1FJL",
                source="NG3K",
                potential=True,
                last_update=now,
                comment="calendar",
            ),
            DXStation(
                callsign="RI1FJL",
                source="DX Summit",
                last_update=now - timedelta(minutes=10),
                comment="spotted",
            ),
        ]
        result = service.deduplicate_stations(stations)
        assert len(result) == 1
        assert result[0].source == "DX Summit"
        assert result[0].potential is False
        assert result[0].sources == ["DX Summit"]

    def test_potential_does_not_replace_live(self, service):
        now = datetime.now(timezone.utc)
        stations = [
            DXStation(
                callsign="RI1FJL",
                source="DX Summit",
                last_update=now - timedelta(minutes=10),
            ),
            DXStation(
                callsign="RI1FJL",
                source="NG3K",
                potential=True,
                last_update=now,
            ),
        ]
        result = service.deduplicate_stations(stations)
        assert result[0].source == "DX Summit"
        assert result[0].potential is False
        assert "NG3K" not in result[0].sources

    def test_potential_kept_when_no_live_spot(self, service):
        now = datetime.now(timezone.utc)
        stations = [
            DXStation(callsign="W1AW", source="DX Summit", last_update=now),
            DXStation(
                callsign="3B8/SQ9UM",
                source="NG3K",
                potential=True,
                last_update=now,
            ),
        ]
        result = service.deduplicate_stations(stations)
        calls = {s.callsign: s for s in result}
        assert "3B8/SQ9UM" in calls
        assert calls["3B8/SQ9UM"].potential is True

    def test_filter_by_age_keeps_potential_even_if_old_timestamp(self, service):
        old = datetime.now(timezone.utc) - timedelta(days=5)
        stations = [
            DXStation(
                callsign="RI1FJL",
                source="NG3K",
                potential=True,
                last_update=old,
            ),
            DXStation(
                callsign="OLD1",
                source="DX Summit",
                last_update=old,
            ),
        ]
        filtered = service.filter_by_age(stations)
        calls = [s.callsign for s in filtered]
        assert "RI1FJL" in calls
        assert "OLD1" not in calls



class TestDatetimeAndActive:
    def test_filter_by_age_accepts_naive_datetime(self, service):
        naive_recent = datetime.now()
        naive_old = datetime.now() - timedelta(hours=5)
        stations = [
            DXStation(callsign="NEW1", source="Test", last_update=naive_recent),
            DXStation(callsign="OLD1", source="Test", last_update=naive_old),
        ]
        filtered = service.filter_by_age(stations)
        callsigns = [s.callsign for s in filtered]
        assert "NEW1" in callsigns
        assert "OLD1" not in callsigns

    def test_get_active_bands_drops_inactive(self, service):
        now = datetime.now(timezone.utc)
        stations = [
            DXStation(callsign="ON", source="Test", status="active", last_update=now),
            DXStation(callsign="OFF", source="Test", status="inactive", last_update=now),
        ]
        active = service.get_active_bands(stations)
        assert [s.callsign for s in active] == ["ON"]

    @pytest.mark.asyncio
    async def test_get_current_data_passes_excluded_sources(self):
        service = DXPeditionService(max_age_seconds=3600, excluded_sources=["pota"])
        with patch("src.service.fetch_all_data") as mock_fetch:
            mock_fetch.return_value = []
            await service.get_current_data()
            args, _kwargs = mock_fetch.call_args
            assert args[1] == ["pota"]

    @pytest.mark.asyncio
    async def test_get_current_data_runs_band_and_dxcc_pipeline(self, service):
        now = datetime.now(timezone.utc)
        with patch("src.service.fetch_all_data") as mock_fetch:
            mock_fetch.return_value = [
                DXStation(
                    callsign="JA1ABC",
                    source="HamQTH",
                    dx_country="Japan",
                    band="",
                    frequency=14.074,
                    last_update=now,
                )
            ]
            summary = await service.get_current_data()
        assert summary.stations[0].band == "20m"
        assert summary.stations[0].dxcc == "339"
