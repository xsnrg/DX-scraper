from datetime import datetime, timezone
import pytest
from src.models import DXStation, DXDataSummary, live_spot_key, station_identity
from pydantic import ValidationError


class MockObject:
    """Mock object for testing model validation"""
    callsign = "MOCK123"
    dx_country = "Mock Country"
    spotter_country = "Mock Spotter Country"
    spotter = "Mock Spotter"
    band = "20m"
    frequency = 14.2
    mode = "SSB"
    comment = "Mock Comment"
    bands = ["20m", "40m"]
    active_band = "20m"
    active_mode = "SSB"
    last_update = datetime.now(timezone.utc)
    source = "test_source"
    status = "active"


class TestDXStation:
    """Tests for DXStation model"""
    def test_dx_station_model_creation(self):
        """Test that DXStation can be created with all required fields"""
        station = DXStation.model_validate(MockObject())
        assert station.callsign == "MOCK123"
        assert station.dx_country == "Mock Country"

    def test_dx_station_model_dump(self):
        """Test model serialization"""
        station = DXStation(
            callsign="TEST123",
            dx_country="Test Country",
            spotter_country="Spotter Country",
            spotter="Test Spotter",
            band="20m",
            frequency=14.2,
            mode="SSB",
            comment="Test Comment",
            last_update=datetime.now(timezone.utc),
            source="test_source",
            status="active"
        )
        dump = station.model_dump()
        assert isinstance(dump, dict)
        assert dump['callsign'] == "TEST123"
        assert dump['dx_country'] == "Test Country"
        assert dump['band'] == "20m"

    def test_dx_station_model_copy(self):
        """Test model copying"""
        station = DXStation(
            callsign="TEST123",
            dx_country="Test Country",
            spotter="Test Spotter",
            band="20m",
            last_update=datetime.now(timezone.utc),
            source="test_source"
        )
        copied = station.model_copy()
        assert copied.callsign == station.callsign
        assert copied is not station

    def test_dx_station_default_last_update_has_tzinfo(self):
        """Test that default last_update has timezone info"""
        station = DXStation(
            callsign="TEST123",
            dx_country="Test Country",
            spotter="Test Spotter",
            band="20m",
            source="test_source"
        )
        assert station.last_update.tzinfo is not None

    def test_dx_station_validation_error_invalid_type(self):
        """Test that DXStation raises validation error for invalid data types"""
        with pytest.raises(ValidationError):
            DXStation(
                callsign=123,
                dx_country="Test Country",
                spotter="Test Spotter",
                band="20m",
                last_update=datetime.now(timezone.utc),
                source="test_source"
            )

    def test_dx_station_validation_error_empty_required_fields(self):
        """Test that DXStation raises validation error for missing required fields"""
        with pytest.raises(ValidationError):
            DXStation(
                callsign="   ",
                dx_country="Test Country",
                spotter="Test Spotter",
                band="20m",
                last_update=datetime.now(timezone.utc),
                source="test_source"
            )

    def test_dx_station_unicode_characters(self):
        """Test DXStation with unicode characters in fields"""
        station = DXStation(
            callsign="P49P",
            dx_country="Palau 🇵🇼",
            spotter="Test Spotter",
            band="20m",
            last_update=datetime.now(timezone.utc),
            source="test_source"
        )
        assert station.dx_country == "Palau 🇵🇼"
        assert station.callsign == "P49P"


    def test_dx_station_optional_field_defaults(self):
        station = DXStation(callsign="W1AW", source="test_source")
        assert station.dxcc == ""
        assert station.pota_reference == ""
        assert station.sources == []
        assert station.frequency is None
        assert station.status == "active"

    def test_dx_station_missing_source_raises(self):
        with pytest.raises(ValidationError):
            DXStation(callsign="W1AW")

    def test_dx_station_stores_dxcc_sources_and_pota(self):
        station = DXStation(
            callsign="W1AW",
            source="POTA",
            dxcc="291",
            pota_reference="US-1234",
            sources=["POTA", "DX Summit"],
        )
        assert station.dxcc == "291"
        assert station.pota_reference == "US-1234"
        assert station.sources == ["POTA", "DX Summit"]


class TestSpotIdentity:
    def test_same_khz_shares_key_even_if_mode_differs(self):
        assert live_spot_key("vp6g", "20m", "cw", 14.023) == live_spot_key("VP6G", "20M", "", 14.0234)

    def test_different_frequencies_have_distinct_keys(self):
        assert live_spot_key("VP6G", "20m", "CW", 14.023) != live_spot_key("VP6G", "40m", "CW", 7.003)

    def test_cw_and_ft8_on_same_band_are_distinct(self):
        assert live_spot_key("VP6G", "20m", "CW", 14.023) != live_spot_key("VP6G", "20m", "FT8", 14.074)

    def test_unmoded_spots_round_to_1_khz(self):
        assert live_spot_key("W1AW", "20m", "", 14.023) != live_spot_key("W1AW", "20m", "", 14.074)
        assert live_spot_key("W1AW", "20m", "", 14.0234) == live_spot_key("W1AW", "20m", "", 14.0231)

    def test_potential_identity_is_callsign_only(self):
        live = DXStation(callsign="VP6G", source="DX Summit", band="20m", mode="CW", frequency=14.023)
        potential = DXStation(callsign="VP6G", source="NG3K", potential=True, band="160-10m")
        assert station_identity(live)[0] == "live"
        assert station_identity(potential) == ("potential", "VP6G")
        assert station_identity(live) != station_identity(potential)



class TestDXDataSummary:
    """Tests for DXDataSummary model"""

    def test_dx_data_summary_creation(self):
        """Test that DXDataSummary can be created with all required fields"""
        summary = DXDataSummary(
            total_stations=10,
            active_stations=8,
            last_refresh=datetime.now(),
            data_sources=["source1", "source2"],
            stations=[]
        )
        assert summary.total_stations == 10
        assert summary.active_stations == 8
        assert summary.data_sources == ["source1", "source2"]

    def test_dx_data_summary_with_stations(self):
        """Test DXDataSummary with actual station data"""
        station = DXStation(
            callsign="TEST123",
            dx_country="Test Country",
            spotter="Test Spotter",
            band="20m",
            last_update=datetime.now(),
            source="test_source"
        )
        
        summary = DXDataSummary(
            total_stations=1,
            active_stations=1,
            last_refresh=datetime.now(),
            data_sources=["test_source"],
            stations=[station]
        )
        assert summary.total_stations == 1
        assert len(summary.stations) == 1
        assert summary.stations[0].callsign == "TEST123"

    def test_dx_data_summary_inherits_from_basemodel(self):
        """Test that DXDataSummary inherits from BaseModel"""
        from pydantic import BaseModel
        assert issubclass(DXDataSummary, BaseModel)

    def test_dx_data_summary_model_dump(self):
        """Test model serialization"""
        station = DXStation(
            callsign="TEST123",
            dx_country="Test Country",
            spotter="Test Spotter",
            band="20m",
            last_update=datetime.now(timezone.utc),
            source="test_source"
        )
        
        summary = DXDataSummary(
            total_stations=1,
            active_stations=1,
            last_refresh=datetime.now(timezone.utc),
            data_sources=["test_source"],
            stations=[station]
        )
        dump = summary.model_dump()
        assert isinstance(dump, dict)
        assert dump['total_stations'] == 1
        assert len(dump['stations']) == 1

    def test_dx_data_summary_model_copy(self):
        """Test model copying"""
        station = DXStation(
            callsign="TEST123",
            dx_country="Test Country",
            spotter="Test Spotter",
            band="20m",
            last_update=datetime.now(timezone.utc),
            source="test_source"
        )
        
        summary = DXDataSummary(
            total_stations=1,
            active_stations=1,
            last_refresh=datetime.now(timezone.utc),
            data_sources=["test_source"],
            stations=[station]
        )
        copied = summary.model_copy()
        assert copied.total_stations == summary.total_stations
        assert copied is not summary

    def test_dx_data_summary_missing_required_fields(self):
        with pytest.raises(ValidationError):
            DXDataSummary(total_stations=1)

