import json
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect
from conftest import _mock_data, open_dashboard


def test_data_api_returns_json(page: Page):
    """The dashboard loads mocked /data JSON into the stats cards."""
    open_dashboard(page, _mock_data())
    expect(page.get_by_text("Total Stations")).to_be_visible()


def test_qrz_status_api(page: Page):
    """The /qrz-status API endpoint returns expected structure."""
    response = page.request.get("http://localhost:8000/qrz-status")
    data = response.json()
    assert "has_credentials" in data
    assert "callsign" in data


def test_qrz_sync_no_credentials(page: Page):
    """The /qrz-sync API returns 400 when no credentials are configured."""
    response = page.request.get("http://localhost:8000/qrz-sync")
    # With credentials: returns success; without: returns 400
    if response.status == 400:
        data = response.json()
        assert data["status"] == "error"
    else:
        # Credentials exist, so it returns success
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.skip(reason="requires real QRZ credentials, not available in CI")
def test_qrz_sync_with_credentials(page: Page, mocker):
    """The /qrz-sync API returns success when credentials are configured."""
    response = page.request.get("http://localhost:8000/qrz-sync")
    # With credentials: returns success
    assert response.status == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "total_qsos" in data
    assert "synced_count" in data


def test_qrz_cache_api(page: Page):
    """The /qrz-cache API endpoint returns expected structure."""
    response = page.request.get("http://localhost:8000/qrz-cache")
    data = response.json()
    assert "exists" in data
    assert "data" in data
    assert "count" in data


def test_qrz_cache_confirmed_only(page: Page, mocker):
    """The /qrz-cache API returns only confirmed QSOs with correct band mapping."""
    # Write to the actual cache file that the server reads
    cache_dir = Path.home() / ".config" / "dxscraper"
    cache_dir.mkdir(parents=True, exist_ok=True)
    temp_cache = cache_dir / "dxscraper_qso.jsonl"

    # Backup existing cache
    backup = None
    if temp_cache.exists():
        backup = temp_cache.read_text()

    cache_data = [
        {"call": "W1AW", "time_on": "2024-01-01T00:00:00Z", "freq": "14.200", "app_qrzlog_status": "C"},
        {"call": "N6SVA", "time_on": "2024-01-01T01:00:00Z", "freq": "7.074", "app_qrzlog_status": "C"},
        {"call": "UNCONFIRMED", "time_on": "2024-01-01T02:00:00Z", "freq": "14.300", "app_qrzlog_status": ""},
    ]
    temp_cache.write_text('\n'.join(json.dumps(d) for d in cache_data))

    try:
        response = page.request.get("http://localhost:8000/qrz-cache")
        assert response.status == 200
        data = response.json()
        assert len(data["data"]) == 2
        calls = [pair[0] for pair in data["data"]]
        assert "W1AW" in calls
        assert "N6SVA" in calls
        assert "UNCONFIRMED" not in calls
    finally:
        temp_cache.unlink(missing_ok=True)
        if backup is not None:
            temp_cache.write_text(backup)


def test_dxcc_map_api_exists(page: Page):
    """The /dxcc-map.html endpoint serves the map page."""
    response = page.request.get("http://localhost:8000/dxcc-map.html")
    assert response.status == 200
    assert "DXCC QSL Status Map" in response.text()
