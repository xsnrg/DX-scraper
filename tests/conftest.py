import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import pytest

DASHBOARD_URL = "http://127.0.0.1:8000"


def pytest_configure(config):
    """Register custom markers for test groups."""
    config.addinivalue_line("markers", "acceptance: mark test as an acceptance test (requires running server)")
    config.addinivalue_line("markers", "unit: mark test as a unit test (runs without server)")


def pytest_collection_modifyitems(config, items):
    """Auto-mark Playwright tests (those using the `page` fixture) as acceptance.

    CI runs `pytest -m acceptance` against a live uvicorn process and
    `pytest -m "not acceptance"` for unit tests, so newly added files are
    picked up without editing the workflow file list.
    """
    for item in items:
        fixturenames = getattr(item, "fixturenames", ())
        if "page" in fixturenames:
            item.add_marker(pytest.mark.acceptance)
        else:
            item.add_marker(pytest.mark.unit)


def _iso_ago(minutes):
    """UTC ISO timestamp `minutes` in the past."""
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _json_fulfill(route, body, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps(body),
    )


def stub_dashboard(
    page,
    data=None,
    *,
    qrz_status=None,
    qrz_cache=None,
    qrz_dxcc=None,
    qrz_all=None,
    qrz_sync=None,
):
    """Intercept dashboard API calls so Playwright tests never hit live /data or QRZ.

    `data` may be a dict or a callable(route) -> dict so tests can vary the
    payload (e.g. POTA exclude_sources).
    """
    if data is None:
        data = _mock_data()

    payloads = {
        "/qrz-status": qrz_status if qrz_status is not None else {
            "has_credentials": False, "callsign": "",
        },
        "/qrz-cache": qrz_cache if qrz_cache is not None else {
            "exists": False, "count": 0, "data": [], "last_modified": "",
        },
        "/qrz-dxcc-numbers": qrz_dxcc if qrz_dxcc is not None else {
            "exists": False, "count": 0, "data": [], "last_modified": "",
        },
        "/qrz-all-data": qrz_all if qrz_all is not None else {
            "exists": False, "count": 0, "data": [], "last_modified": "",
        },
        "/qrz-sync": qrz_sync if qrz_sync is not None else {"status": "ok"},
        "/qrz-token": {"status": "ok"},
    }

    def on_data(route, request=None):
        url = route.request.url
        if urlparse(url).path != "/data":
            route.fallback()
            return
        payload = data(route) if callable(data) else data
        _json_fulfill(route, payload)

    page.route("**/data*", on_data)
    for path, body in payloads.items():
        def handler(route, request=None, b=body):
            _json_fulfill(route, b)
        page.route(f"**{path}*", handler)


def open_dashboard(page, data=None, **kwargs):
    """Stub APIs, open the dashboard, wait until the table chrome is up."""
    stub_dashboard(page, data=data, **kwargs)
    page.goto(DASHBOARD_URL)


def qrz_ready_kwargs(dxcc_numbers=None, cache_data=None, all_data=None, callsign="TEST"):
    """QRZ stubs for tests that need credentials + a populated cache."""
    cache_data = cache_data if cache_data is not None else [["W1AW", "40M", "291"]]
    dxcc_numbers = dxcc_numbers if dxcc_numbers is not None else ["291"]
    all_data = all_data if all_data is not None else [["W1AW", "40M", "C"]]
    return dict(
        qrz_status={"has_credentials": True, "callsign": callsign},
        qrz_cache={
            "exists": True, "count": len(cache_data),
            "data": cache_data, "last_modified": "",
        },
        qrz_dxcc={
            "exists": True, "count": len(dxcc_numbers),
            "data": dxcc_numbers, "last_modified": "",
        },
        qrz_all={
            "exists": True, "count": len(all_data),
            "data": all_data, "last_modified": "",
        },
    )


def _mock_data(num_stations=15):
    """Generate mock DX data with realistic callsigns and countries."""
    now = datetime.now(timezone.utc).isoformat()

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
    for s in stations_data[:num_stations]:
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
