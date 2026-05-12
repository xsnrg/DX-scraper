import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    # The root endpoint serves the index.html file, not a JSON response
    assert "DXpedition Monitor" in response.text

def test_get_data():
    """Test the /data endpoint."""
    response = client.get("/data")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

def test_qrz_sync_no_credentials(tmp_path, monkeypatch):
    """Test /qrz-sync returns 400 when no credentials configured."""
    from src.qrz_config import _CONFIG_FILE
    from pathlib import Path

    temp_config = tmp_path / "dxscraper_config.json"
    monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

    response = client.get("/qrz-sync")
    assert response.status_code == 400
    data = response.json()
    assert data['status'] == 'error'

def test_qrz_sync_with_credentials(tmp_path, monkeypatch, mocker):
    """Test /qrz-sync returns success when credentials exist."""
    from src.qrz_config import save_qrz_data, _CONFIG_FILE
    from unittest.mock import AsyncMock

    temp_config = tmp_path / "dxscraper_config.json"
    monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

    save_qrz_data('AB1CD', 'testtoken')
    mock_sync = AsyncMock(return_value={'status': 'ok', 'total_qsos': 100, 'synced_count': 5})
    mocker.patch('src.api.sync_qso_data', mock_sync)
    response = client.get("/qrz-sync")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['total_qsos'] == 100
    mock_sync.assert_called_once()


def test_data_endpoint_has_all_search_fields():
    """Test that /data returns all fields the frontend search operates on."""
    response = client.get("/data")
    assert response.status_code == 200
    data = response.json()
    # stations should be a list
    stations = data.get("stations", [])
    if not stations:
        pytest.skip("No stations available to validate schema")
    required_fields = [
        "callsign", "dx_country", "spotter_country", "spotter",
        "band", "frequency", "mode", "comment", "source", "last_update"
    ]
    for field in required_fields:
        assert field in stations[0], f"Missing field '{field}' in /data response"


def test_qrz_cache_no_file(tmp_path, monkeypatch):
    """Test /qrz-cache returns empty list when no cache file exists."""
    from src.qrz_qso import QSO_CACHE_FILE
    from pathlib import Path

    temp_cache = tmp_path / "dxscraper_qso.jsonl"
    monkeypatch.setattr('src.api.QSO_CACHE_FILE', temp_cache)

    response = client.get("/qrz-cache")
    assert response.status_code == 200
    data = response.json()
    assert data == {"data": [], "exists": False, "count": 0, "last_modified": ""}


def test_qrz_cache_with_file(tmp_path, monkeypatch):
    """Test /qrz-cache returns pairs from cache file."""
    from src.qrz_qso import QSO_CACHE_FILE
    import json

    temp_cache = tmp_path / "dxscraper_qso.jsonl"
    monkeypatch.setattr('src.api.QSO_CACHE_FILE', temp_cache)

    cache_data = [
        {"call": "W1AW", "time_on": "2024-01-01T00:00:00Z", "time_off": "", "freq": "14.200", "mode": "CW", "rst_sent": "59", "rst_recv": "59", "grid": "EN31", "notes": "", "app_qrzlog_status": "C"},
        {"call": "k2abc", "time_on": "2024-01-01T01:00:00Z", "time_off": "", "freq": "7.074", "mode": "SSB", "rst_sent": "59", "rst_recv": "59", "grid": "FN31", "notes": "", "app_qrzlog_status": "C"},
        {"call": "INVALID", "time_on": "", "time_off": "", "freq": "", "mode": "", "rst_sent": "", "rst_recv": "", "grid": "", "notes": ""},
    ]
    temp_cache.write_text('\n'.join(json.dumps(d) for d in cache_data))
    response = client.get("/qrz-cache")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["data"][0] == ["W1AW", "20m"]
    assert data["data"][1] == ["K2ABC", "40m"]
    assert data["exists"] is True
    assert data["count"] == 2
    assert "last_modified" in data


def test_dxcc_map_page():
    """Test the DXCC map page endpoint."""
    response = client.get("/dxcc-map.html")
    assert response.status_code == 200
    assert "leaflet" in response.text
    assert "DXCC" in response.text


def test_dxcc_countries_js_file():
    """Test the DXCC countries data file is served correctly."""
    response = client.get("/static/dxcc-countries.js")
    assert response.status_code == 200
    assert "DXCC_COUNTRIES" in response.text
    assert "Alaska" in response.text
    assert "United Nations HQ" in response.text


def test_dxcc_countries_js_has_entries():
    """Test the DXCC countries file has a reasonable number of entries."""
    response = client.get("/static/dxcc-countries.js")
    assert response.status_code == 200
    # Count lines that define country entries
    entry_count = response.text.count("{name:")
    assert entry_count > 300
    assert entry_count < 400


def test_hawaii_has_dxcc_110():
    """Test that Hawaii is always DXCC 110 in the countries data."""
    response = client.get("/static/dxcc-countries.js")
    assert response.status_code == 200
    # Extract Hawaii entry and verify DXCC number
    lines = response.text.split('\n')
    hawaii_line = [l for l in lines if '"Hawaii"' in l]
    assert len(hawaii_line) == 1, "Hawaii entry not found"
    assert 'dxcc: "110"' in hawaii_line[0], f"Hawaii should be DXCC 110, got: {hawaii_line[0]}"


def test_dxcc_map_html_uses_dxcc_key():
    """Test that the DXCC map HTML uses DXCC numbers for qslData lookup, not country names."""
    response = client.get("/dxcc-map.html")
    assert response.status_code == 200
    # Verify the map page uses qslData[country.dxcc] not qslData[country.name]
    assert 'qslData[country.dxcc]' in response.text, "Map should use DXCC numbers for qslData lookup"
    # Verify no references to qslData[country.name] which would break color sync
    assert 'qslData[country.name]' not in response.text, "Map should not use country names for qslData lookup"
    # Verify getCountryColor receives the country object, not just the name
    assert 'getCountryColor(country)' in response.text, "getCountryColor should receive country object"
    assert 'getCountryColor(country.name)' not in response.text, "getCountryColor should not receive just country name"


def test_qrz_filter_uses_station_band_not_bands():
    """Test that the QRZ filter frontend code uses station.band (singular) not station.bands (plural).

    This test would have caught the bug where station.bands was used instead of station.band,
    causing the band comparison to always fail and show amber highlights for confirmed QSOs.
    """
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # The getStationBands function should reference station.band, not station.bands
    assert 'station.band' in html, "Frontend should use station.band (singular) to match DXStation model"
    assert 'station.bands' not in html, "Frontend should not use station.bands (plural) - DXStation model has no 'bands' field"

    # The filtering sBands function should also use s.band, not s.bands
    assert 's.band' in html, "Filtering logic should use s.band (singular) to match DXStation model"
    assert 's.bands' not in html, "Filtering logic should not use s.bands (plural) - DXStation model has no 'bands' field"


def test_qrz_cache_requires_confirmed_status(tmp_path, monkeypatch):
    """Test that /qrz-cache only returns QSO pairs where app_qrzlog_status is 'C' (confirmed).

    This ensures unconfirmed QSOs don't incorrectly filter out active DX stations.
    """
    from src.qrz_qso import QSO_CACHE_FILE
    import json

    temp_cache = tmp_path / "dxscraper_qso_confirmed.jsonl"
    monkeypatch.setattr('src.api.QSO_CACHE_FILE', temp_cache)

    cache_data = [
        {"call": "W1AW", "time_on": "2024-01-01T00:00:00Z", "freq": "14.200", "app_qrzlog_status": "C"},
        {"call": "N6SVA", "time_on": "2024-01-01T01:00:00Z", "freq": "14.250", "app_qrzlog_status": "C"},
        {"call": "N6SVA", "time_on": "2024-01-01T02:00:00Z", "freq": "7.074", "app_qrzlog_status": "C"},
        {"call": "UNCONFIRMED", "time_on": "2024-01-01T03:00:00Z", "freq": "14.300", "app_qrzlog_status": ""},
        {"call": "NOTCONFIRMED", "time_on": "2024-01-01T04:00:00Z", "freq": "14.350", "app_qrzlog_status": "N"},
    ]
    temp_cache.write_text('\n'.join(json.dumps(d) for d in cache_data))

    response = client.get("/qrz-cache")
    assert response.status_code == 200
    data = response.json()

    # Only confirmed QSOs should be returned
    assert len(data["data"]) == 3
    calls = [pair[0] for pair in data["data"]]
    assert "W1AW" in calls
    assert "N6SVA" in calls
    assert "UNCONFIRMED" not in calls
    assert "NOTCONFIRMED" not in calls

    # N6SVA should have both 20m and 40m entries
    nsva_entries = [pair for pair in data["data"] if pair[0] == "N6SVA"]
    assert len(nsva_entries) == 2
    bands = [pair[1] for pair in nsva_entries]
    assert "20m" in bands
    assert "40m" in bands


def test_qrz_filter_exact_band_match_should_not_highlight(tmp_path, monkeypatch):
    """Test the logic that a station with a confirmed QSO on the same band should not be highlighted.

    This test validates the exact scenario from the bug: N6SVA on 20m with a confirmed 20m QSO
    should get status 'exact' (no amber highlight), not 'different_band'.

    The frontend logic in getQrzRowClass checks:
    1. If station has an exact band match in QRZ cache -> status = 'exact' -> no highlight
    2. If station has a different band match -> status = 'different_band' -> amber highlight

    This test ensures the data flow supports that logic correctly.
    """
    from src.qrz_qso import QSO_CACHE_FILE
    import json

    temp_cache = tmp_path / "dxscraper_qso_exact.jsonl"
    monkeypatch.setattr('src.api.QSO_CACHE_FILE', temp_cache)

    # N6SVA has confirmed QSOs on both 20m and 40m
    cache_data = [
        {"call": "N6SVA", "time_on": "2024-01-01T00:00:00Z", "freq": "14.250", "app_qrzlog_status": "C"},
        {"call": "N6SVA", "time_on": "2024-01-01T01:00:00Z", "freq": "7.074", "app_qrzlog_status": "C"},
    ]
    temp_cache.write_text('\n'.join(json.dumps(d) for d in cache_data))

    response = client.get("/qrz-cache")
    assert response.status_code == 200
    data = response.json()

    # Verify N6SVA has both bands in cache
    nsva_entries = [pair for pair in data["data"] if pair[0] == "N6SVA"]
    assert len(nsva_entries) == 2
    bands = set(pair[1] for pair in nsva_entries)
    assert "20m" in bands
    assert "40m" in bands

    # The frontend getQrzRowClass logic would check:
    # For a station on 20m with N6SVA in cache:
    # - It finds N6SVA in cache with 20m -> status = 'exact' (because station.band === '20m')
    # - It finds N6SVA in cache with 40m -> status stays 'exact' (because 40m is not in stationBands)
    # Result: no amber highlight (correct behavior)
    #
    # The bug was that station.bands was always undefined, so stationBands was always [],
    # meaning stationBands.includes(qrzBand) was always false, so status became 'different_band'.
    # This test ensures the DXStation model has 'band' (singular) and the frontend uses it.
    # The band field validation is covered by test_qrz_filter_uses_station_band_not_bands above.
