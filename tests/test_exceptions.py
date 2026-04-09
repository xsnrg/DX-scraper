import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from exceptions import DXDataError, DataSourceError, DataValidationException, DataStalenessException


class TestDXDataError:
    """Tests for DXDataError base exception class"""

    def test_dx_data_error_creation(self):
        """Test that DXDataError can be created with a message"""
        error = DXDataError("Test error message")
        assert str(error) == "Test error message"

    def test_dx_data_error_inherits_from_exception(self):
        """Test that DXDataError inherits from Exception"""
        assert issubclass(DXDataError, Exception)

    def test_dx_data_error_default_message(self):
        """Test DXDataError with no message (default empty string)"""
        error = DXDataError()
        assert str(error) == ""

    def test_dx_data_error_raised(self):
        """Test that DXDataError can be raised and caught"""
        with pytest.raises(DXDataError) as exc_info:
            raise DXDataError("Test exception")
        assert "Test exception" in str(exc_info.value)


class TestDataSourceError:
    """Tests for DataSourceError exception class"""

    def test_datasource_error_creation(self):
        """Test DataSourceError with source, message, and no original error"""
        error = DataSourceError("api", "Connection failed")
        assert error.source == "api"
        assert error.message == "Connection failed"
        assert error.original_error is None
        assert "Error from api: Connection failed" in str(error)

    def test_datasource_error_with_original_error(self):
        """Test DataSourceError with original exception"""
        original = ValueError("Original error")
        error = DataSourceError("database", "Query failed", original_error=original)
        assert error.source == "database"
        assert error.message == "Query failed"
        assert error.original_error is original
        assert "Error from database: Query failed" in str(error)

    def test_datasource_error_raised(self):
        """Test that DataSourceError can be raised and caught"""
        with pytest.raises(DataSourceError) as exc_info:
            raise DataSourceError("external_api", "Timeout", original_error=TimeoutError())
        assert exc_info.value.source == "external_api"
        assert "Timeout" in str(exc_info.value)


class TestDataValidationException:
    """Tests for DataValidationException exception class"""

    def test_data_validation_exception_creation(self):
        """Test DataValidationException can be created"""
        error = DataValidationException()
        assert isinstance(error, DXDataError)
        assert isinstance(error, Exception)

    def test_data_validation_exception_raised(self):
        """Test that DataValidationException can be raised and caught"""
        with pytest.raises(DataValidationException) as exc_info:
            raise DataValidationException()
        assert isinstance(exc_info.value, DataValidationException)


class TestDataStalenessException:
    """Tests for DataStalenessException exception class"""

    def test_data_staleness_exception_creation(self):
        """Test DataStalenessException with max_age and actual_age"""
        error = DataStalenessException(max_age=300, actual_age=600)
        assert error.max_age == 300
        assert error.actual_age == 600
        expected_msg = "Data is too old. Max age: 300s, Actual age: 600s"
        assert str(error) == expected_msg

    def test_data_staleness_exception_with_equal_ages(self):
        """Test DataStalenessException when actual_age equals max_age"""
        error = DataStalenessException(max_age=100, actual_age=100)
        assert error.max_age == 100
        assert error.actual_age == 100
        assert "Data is too old. Max age: 100s, Actual age: 100s" in str(error)

    def test_data_staleness_exception_raised(self):
        """Test that DataStalenessException can be raised and caught"""
        with pytest.raises(DataStalenessException) as exc_info:
            raise DataStalenessException(max_age=60, actual_age=120)
        assert exc_info.value.max_age == 60
        assert exc_info.value.actual_age == 120
        assert "Data is too old" in str(exc_info.value)
