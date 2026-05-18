import pytest


def pytest_configure(config):
    """Register custom markers for test groups."""
    config.addinivalue_line("markers", "acceptance: mark test as an acceptance test (requires running server)")
    config.addinivalue_line("markers", "unit: mark test as a unit test (runs without server)")


def _mock_data(num_stations=15):
    """Generate mock DX data with realistic callsigns and countries."""
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    stations_data = [
        {"callsign": "W1AW", "dx_country": "USA", "spotter_country": "USA", "spotter": "N1AR", "band": "40m", "frequency": 7.074, "mode": "SSB", "comment": "DXpedition", "source": "DX Summit", "pota_reference": None},
        {"callsign": "VK3EPR", "dx_country": "Australia", "spotter_country": "USA", "spotter": "K1AR", "band": "20m", "frequency": 14.250, "mode": "CW", "comment": "Rare DX", "source": "DX Cluster", "pota_reference": None},
        {"callsign": "P29V", "dx_country": "Sao Tome and Principe", "spotter_country": "Brazil", "spotter": "PY2OS", "band": None, "frequency": 14.270, "mode": "FT8", "comment": "SOTA activation", "source": "POTA", "pota_reference": "POTA-12345"},
        {"callsign": "ZS6DX", "dx_country": "South Africa", "spotter_country": "Germany", "spotter": "DL1ABC", "band": "15m", "frequency": 21.250, "mode": "SSB", "comment": "DXpedition", "source": "DX Summit", "pota_reference": None},
        {"callsign": "JA1RAT", "dx_country": "Japan", "spotter_country": "USA", "spotter": "W6XYZ", "band": "10m", "frequency": 28.500, "mode": "CW", "comment": "Contest", "source": "DX Cluster", "pota_reference": None},
        {"callsign": "VP8LTI", "dx_country": "South Georgia", "spotter_country": "UK", "spotter": "G4ABC", "band": "40m", "frequency": 7.100, "mode": "FT8", "comment": "Rare DX", "source": "DX Summit", "pota_reference": None},
        {"callsign": "A45A", "dx_country": "Oman", "spotter_country": "France", "spotter": "F5DEF", "band": "20m", "frequency": 14.280, "mode": "SSB", "comment": "DXpedition", "source": "DX Cluster", "pota_reference": None},
        {"callsign": "YI5A", "dx_country": "Iraq", "spotter_country": "USA", "spotter": "K1ABC", "band": "17m", "frequency": 18.100, "mode": "CW", "comment": "DXpedition", "source": "DX Summit", "pota_reference": None},
        {"callsign": "S79M", "dx_country": "Seychelles", "spotter_country": "South Africa", "spotter": "ZS1ABC", "band": "30m", "frequency": 10.120, "mode": "FT8", "comment": "Rare DX", "source": "DX Cluster", "pota_reference": None},
        {"callsign": "3B8C", "dx_country": "Rodrigues", "spotter_country": "Mauritius", "spotter": "M1ABC", "band": "15m", "frequency": 21.300, "mode": "SSB", "comment": "DXpedition", "source": "DX Summit", "pota_reference": None},
        {"callsign": "A25Y", "dx_country": "Botswana", "spotter_country": "UK", "spotter": "G7XYZ", "band": "20m", "frequency": 14.230, "mode": "CW", "comment": "DXpedition", "source": "DX Cluster", "pota_reference": None},
        {"callsign": "C6AF", "dx_country": "Tuvalu", "spotter_country": "Australia", "spotter": "VK2ABC", "band": "40m", "frequency": 7.080, "mode": "SSB", "comment": "DXpedition", "source": "DX Summit", "pota_reference": None},
        {"callsign": "V31K", "dx_country": "Belize", "spotter_country": "USA", "spotter": "W5DEF", "band": "80m", "frequency": 3.650, "mode": "FT8", "comment": "SOTA", "source": "POTA", "pota_reference": "POTA-67890"},
        {"callsign": "P40R", "dx_country": "Curacao", "spotter_country": "Netherlands", "spotter": "PA0ABC", "band": "10m", "frequency": 28.450, "mode": "SSB", "comment": "DXpedition", "source": "DX Summit", "pota_reference": None},
        {"callsign": "8P9A", "dx_country": "Aruba", "spotter_country": "USA", "spotter": "W9ABC", "band": "15m", "frequency": 21.350, "mode": "CW", "comment": "DXpedition", "source": "DX Cluster", "pota_reference": None},
    ]
    
    stations = []
    for i, s in enumerate(stations_data[:num_stations]):
        station = dict(s)
        station["sources"] = [s["source"]]
        station["last_update"] = now
        stations.append(station)
    
    return {
        "total_stations": len(stations),
        "active_stations": len(stations),
        "last_refresh": now,
        "data_sources": [],
        "stations": stations,
    }
