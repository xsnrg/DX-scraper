import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

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
    entry_count = response.text.count("{name:")
    assert entry_count > 300
    assert entry_count < 400


def test_hawaii_has_dxcc_110():
    """Test that Hawaii is always DXCC 110 in the countries data."""
    response = client.get("/static/dxcc-countries.js")
    assert response.status_code == 200
    lines = response.text.split('\n')
    hawaii_line = [l for l in lines if '"Hawaii"' in l]
    assert len(hawaii_line) == 1, "Hawaii entry not found"
    assert 'dxcc: "110"' in hawaii_line[0], f"Hawaii should be DXCC 110, got: {hawaii_line[0]}"


def test_dxcc_map_html_uses_dxcc_key():
    """Test that the DXCC map HTML uses DXCC numbers for qslData lookup, not country names."""
    response = client.get("/dxcc-map.html")
    assert response.status_code == 200
    assert 'qslData[country.dxcc]' in response.text, "Map should use DXCC numbers for qslData lookup"
    assert 'qslData[country.name]' not in response.text, "Map should not use country names for qslData lookup"
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

    assert 'station.band' in html, "Frontend should use station.band (singular) to match DXStation model"
    assert 'station.bands' not in html, "Frontend should not use station.bands (plural) - DXStation model has no 'bands' field"

    assert 's.band' in html, "Filtering logic should use s.band (singular) to match DXStation model"
    assert 's.bands' not in html, "Filtering logic should not use s.bands (plural) - DXStation model has no 'bands' field"


def test_qrz_cache_requires_confirmed_status(tmp_path, monkeypatch):
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

    assert len(data["data"]) == 3
    calls = [pair[0] for pair in data["data"]]
    assert "W1AW" in calls
    assert "N6SVA" in calls
    assert "UNCONFIRMED" not in calls
    assert "NOTCONFIRMED" not in calls

    nsva_entries = [pair for pair in data["data"] if pair[0] == "N6SVA"]
    assert len(nsva_entries) == 2
    bands = [pair[1] for pair in nsva_entries]
    assert "20m" in bands
    assert "40m" in bands


def test_qrz_filter_exact_band_match_should_not_highlight(tmp_path, monkeypatch):
    from src.qrz_qso import QSO_CACHE_FILE
    import json

    temp_cache = tmp_path / "dxscraper_qso_exact.jsonl"
    monkeypatch.setattr('src.api.QSO_CACHE_FILE', temp_cache)

    cache_data = [
        {"call": "N6SVA", "time_on": "2024-01-01T00:00:00Z", "freq": "14.250", "app_qrzlog_status": "C"},
        {"call": "N6SVA", "time_on": "2024-01-01T01:00:00Z", "freq": "7.074", "app_qrzlog_status": "C"},
    ]
    temp_cache.write_text('\n'.join(json.dumps(d) for d in cache_data))

    response = client.get("/qrz-cache")
    assert response.status_code == 200
    data = response.json()

    nsva_entries = [pair for pair in data["data"] if pair[0] == "N6SVA"]
    assert len(nsva_entries) == 2
    bands = set(pair[1] for pair in nsva_entries)
    assert "20m" in bands
    assert "40m" in bands

def test_data_endpoint_exclude_sources_parameter():
    """Test that exclude_sources parameter is properly parsed and doesn't cause 404."""
    response = client.get("/data?exclude_sources=POTA")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

def test_data_endpoint_multiple_exclude_sources():
    """Test that multiple exclude sources are properly comma-separated."""
    response = client.get("/data?exclude_sources=POTA,dx_news")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

def test_clickable_band_column_in_dashboard():
    """Test that the Band column has clickable spans with search binding."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert '@click="searchQuery' in html
    assert "station.band" in html
    assert "cursor-pointer" in html

def test_clickable_mode_column_in_dashboard():
    """Test that the Mode column has clickable spans with search binding."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "station.mode" in html
    assert "station.comment" in html
    assert "cursor-pointer" in html

def test_clickable_dx_location_column_in_dashboard():
    """Test that the DX Location column has clickable spans with search binding."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "station.dx_country" in html
    assert "cursor-pointer" in html

def test_clear_search_button_in_dashboard():
    """Test that the search input has a clear button."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "fa-times" in html
    assert "searchQuery = ''" in html
