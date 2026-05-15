import pytest


def pytest_configure(config):
    """Register custom markers for test groups."""
    config.addinivalue_line("markers", "acceptance: mark test as an acceptance test (requires running server)")
    config.addinivalue_line("markers", "unit: mark test as a unit test (runs without server)")
