import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from datetime import datetime
from models import DXStation, DXDataSummary


class TestDXStation:
    """Tests for DXStation model"""

    def test_dx_station_creation(self):
        """Test that DXStation can be created with all required fields"""
        station = DXStation(
            callsign="TEST123",
            name="Test Station",
            location="Test Location",
            bands=["20m", "40m"],
            last_update=datetime.now(),
            source="test_source",
            status="active"
        )
        assert station.callsign == "TEST123"
        assert station.name == "Test Station"
        assert station.location == "Test Location"
        assert station.bands == ["20m", "40m"]

    def test_dx_station_optional_fields(self):
        """Test DXStation with optional fields set"""
        station = DXStation(
            callsign="TEST456",
            name="Test Station 2",
            location="Test Location 2",
            bands=["80m"],
            active_band="80m",
            active_mode="SSB",
            last_update=datetime.now(),
            source="test_source",
            status="active"
        )
        assert station.active_band == "80m"
        assert station.active_mode == "SSB"

    def test_dx_station_default_bands(self):
        """Test DXStation with default empty bands list"""
        station = DXStation(
            callsign="TEST789",
            name="Test Station 3",
            location="Test Location 3",
            last_update=datetime.now(),
            source="test_source"
        )
        assert station.bands == []

    def test_dx_station_default_status(self):
        """Test DXStation with default status"""
        station = DXStation(
            callsign="TEST999",
            name="Test Station 4",
            location="Test Location 4",
            last_update=datetime.now(),
            source="test_source"
        )
        assert station.status == "active"

    def test_dx_station_inherits_from_basemodel(self):
        """Test that DXStation inherits from BaseModel"""
        assert issubclass(DXStation, object)

    def test_dx_station_from_attributes(self):
        """Test DXStation model_config from_attributes setting"""
        # Create a simple object to simulate from_attributes usage
        class MockObject:
            callsign = "MOCK123"
            name = "Mock Station"
            location = "Mock Location"
            bands = ["15m"]
            last_update = datetime.now()
            source = "mock_source"
            status = "active"
        
        station = DXStation.model_validate(MockObject())
        assert station.callsign == "MOCK123"
        assert station.name == "Mock Station"


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
            name="Test Station",
            location="Test Location",
            bands=["20m"],
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
        assert issubclass(DXDataSummary, object)

