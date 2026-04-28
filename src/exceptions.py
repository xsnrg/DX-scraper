class DXDataError(Exception):
    """Base exception for DX data errors"""
    pass


class DataSourceError(DXDataError):
    """Error when fetching data from a source"""
    def __init__(self, source: str, message: str, original_error: Exception = None):
        self.source = source
        self.message = message
        self.original_error = original_error
        super().__init__(f"Error from {source}: {message}")


class DataValidationException(DXDataError):
    """Error when data validation fails"""
    pass


class DataStalenessException(DXDataError):
    """Error when data is too old"""
    def __init__(self, max_age: int, actual_age: int):
        self.max_age = max_age
        self.actual_age = actual_age
        super().__init__(f"Data is too old. Max age: {max_age}s, Actual age: {actual_age}s")


class QRZDataError(DXDataError):
    """Error when fetching QSO data from QRZ"""
    def __init__(self, message: str):
        super().__init__(f"QRZ QSO error: {message}")
