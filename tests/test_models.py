from datetime import datetime, timezone
import pytest
from src.models import DXStation, DXDataSummary
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
