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
        {"call": "W1AW", "time_on": "2024-01-01T00:00:00Z", "time_off": "", "freq": "14.200", "mode": "CW", "rst_sent": "59", "rst_recv": "59", "grid": "EN31", "notes": ""},
        {"call": "k2abc", "time_on": "2024-01-01T01:00:00Z", "time_off": "", "freq": "7.074", "mode": "SSB", "rst_sent": "59", "rst_recv": "59", "grid": "FN31", "notes": ""},
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
