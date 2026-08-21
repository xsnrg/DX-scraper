"""Unit tests for FastAPI routes using TestClient (no live server)."""
import json
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api import app
from src.models import DXDataSummary, DXStation

client = TestClient(app)


def _write_cache(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


class TestRootAndStatic:
    def test_root_serves_dashboard(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "DXpedition Monitor" in response.text

    def test_favicon_served(self):
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert response.headers["content-type"] in (
            "image/x-icon",
            "image/vnd.microsoft.icon",
            "application/octet-stream",
        )

    def test_dxcc_map_served(self):
        response = client.get("/dxcc-map.html")
        assert response.status_code == 200
        assert "DXCC QSL Status Map" in response.text


class TestDataEndpoint:
    def test_exclude_sources_passed_to_service(self):
        captured = {}

        class FakeService:
            def __init__(self, max_age, excluded_sources=None):
                captured["max_age"] = max_age
                captured["excluded"] = excluded_sources

            async def get_current_data(self):
                return DXDataSummary(
                    total_stations=0,
                    active_stations=0,
                    data_sources=[],
                    stations=[],
                )

        with patch("src.api.DXPeditionService", FakeService):
            response = client.get("/data?exclude_sources=POTA,%20dx_news")

        assert response.status_code == 200
        assert captured["excluded"] == ["POTA", "dx_news"]

    def test_data_without_exclude_does_not_pass_excluded_sources(self):
        captured = {}

        class FakeService:
            def __init__(self, max_age, excluded_sources=None):
                captured["kwargs_excluded"] = excluded_sources
                captured["argcount"] = 1 if excluded_sources is None else 2

            async def get_current_data(self):
                station = DXStation(
                    callsign="W1AW",
                    source="DX Summit",
                    last_update=datetime.now(timezone.utc),
                )
                return DXDataSummary(
                    total_stations=1,
                    active_stations=1,
                    data_sources=["DX Summit"],
                    stations=[station],
                )

        with patch("src.api.DXPeditionService", FakeService):
            response = client.get("/data")

        assert response.status_code == 200
        assert captured["kwargs_excluded"] is None
        body = response.json()
        assert body["total_stations"] == 1
        assert body["stations"][0]["callsign"] == "W1AW"


class TestQrzStatus:
    def test_token_masking_long_token(self, monkeypatch):
        monkeypatch.setattr(
            "src.api.get_qrz_data",
            lambda: {"callsign": "W1AW", "token": "abcdefghij", "keyring_unavailable": False},
        )
        response = client.get("/qrz-status")
        data = response.json()
        assert data["callsign"] == "W1AW"
        assert data["has_credentials"] is True
        assert data["token_masked"] == "****ghij"
        assert data["keyring_unavailable"] is False

    def test_token_masking_short_token(self, monkeypatch):
        monkeypatch.setattr(
            "src.api.get_qrz_data",
            lambda: {"callsign": "W1AW", "token": "abc", "keyring_unavailable": False},
        )
        response = client.get("/qrz-status")
        data = response.json()
        assert data["token_masked"] == "****"
        assert data["has_credentials"] is True

    def test_no_credentials(self, monkeypatch):
        monkeypatch.setattr(
            "src.api.get_qrz_data",
            lambda: {"callsign": "", "token": "", "keyring_unavailable": True},
        )
        response = client.get("/qrz-status")
        data = response.json()
        assert data["has_credentials"] is False
        assert data["keyring_unavailable"] is True


class TestQrzSyncNoCredentials:
    def test_returns_400_when_credentials_missing(self, monkeypatch):
        monkeypatch.setattr(
            "src.api.get_qrz_data",
            lambda: {"callsign": "", "token": ""},
        )
        response = client.get("/qrz-sync")
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "not configured" in data["error"]


class TestQrzCacheEndpoints:
    def test_missing_cache_exists_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.api.QSO_CACHE_FILE", tmp_path / "missing.jsonl")
        for path in ("/qrz-cache", "/qrz-dxcc-numbers", "/qrz-all-data", "/qrz-qso-data"):
            response = client.get(path)
            assert response.status_code == 200, path
            data = response.json()
            assert data["exists"] is False
            assert data["count"] == 0
            assert data["data"] == []

    def test_qrz_cache_confirmed_only_with_band(self, tmp_path, monkeypatch):
        cache = tmp_path / "dxscraper_qso.jsonl"
        monkeypatch.setattr("src.api.QSO_CACHE_FILE", cache)
        _write_cache(cache, [
            {"call": "W1AW", "freq": "14.200", "app_qrzlog_status": "C", "dxcc": "291"},
            {"call": "n6sva", "freq": "7.074", "app_qrzlog_status": "C", "dxcc": "291"},
            {"call": "UNCONFIRMED", "freq": "14.300", "app_qrzlog_status": "", "dxcc": "291"},
            {"call": "NOBAND", "freq": "", "app_qrzlog_status": "C", "dxcc": "291"},
            {"call": "BADFREQ", "freq": "not-a-number", "app_qrzlog_status": "C", "dxcc": "291"},
        ])
        cache.write_text(cache.read_text() + "not json\n\n")

        response = client.get("/qrz-cache")
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        calls = [pair[0] for pair in data["data"]]
        assert calls == ["W1AW", "N6SVA"]
        bands = {pair[0]: pair[1] for pair in data["data"]}
        assert bands["W1AW"] == "20m"
        assert bands["N6SVA"] == "40m"
        assert data["count"] == 2
        assert data["last_modified"]

    def test_qrz_dxcc_numbers_sorted_and_stripped(self, tmp_path, monkeypatch):
        cache = tmp_path / "dxscraper_qso.jsonl"
        monkeypatch.setattr("src.api.QSO_CACHE_FILE", cache)
        _write_cache(cache, [
            {"call": "A", "app_qrzlog_status": "C", "dxcc": "0291"},
            {"call": "B", "app_qrzlog_status": "C", "dxcc": "50"},
            {"call": "C", "app_qrzlog_status": "C", "dxcc": "50"},
            {"call": "D", "app_qrzlog_status": "", "dxcc": "339"},
            {"call": "E", "app_qrzlog_status": "C", "dxcc": ""},
            {"call": "F", "app_qrzlog_status": "C", "dxcc": "000"},
        ])

        response = client.get("/qrz-dxcc-numbers")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == ["50", "291"]
        assert data["count"] == 2
        assert data["exists"] is True

    def test_qrz_all_data_includes_unconfirmed(self, tmp_path, monkeypatch):
        cache = tmp_path / "dxscraper_qso.jsonl"
        monkeypatch.setattr("src.api.QSO_CACHE_FILE", cache)
        _write_cache(cache, [
            {"call": "W1AW", "freq": "14.200", "app_qrzlog_status": "C"},
            {"call": "K1ABC", "freq": "7.074", "app_qrzlog_status": "N"},
            {"call": "NOBAND", "freq": "", "app_qrzlog_status": "C"},
        ])

        response = client.get("/qrz-all-data")
        assert response.status_code == 200
        data = response.json()
        triples = {(row[0], row[1], row[2]) for row in data["data"]}
        assert ("W1AW", "20m", "C") in triples
        assert ("K1ABC", "40m", "N") in triples
        assert data["count"] == 2

    def test_qrz_qso_data_fields(self, tmp_path, monkeypatch):
        cache = tmp_path / "dxscraper_qso.jsonl"
        monkeypatch.setattr("src.api.QSO_CACHE_FILE", cache)
        _write_cache(cache, [
            {
                "call": "W1AW",
                "country": "United States",
                "dxcc": "291",
                "app_qrzlog_status": "C",
                "time_on": "2024-01-01T00:00:00Z",
                "freq": "14.200",
                "mode": "CW",
            },
            {"call": "SKIPME"},
        ])
        cache.write_text(cache.read_text() + "{bad json\n")

        response = client.get("/qrz-qso-data")
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["count"] == 2
        first = data["data"][0]
        assert first["call"] == "W1AW"
        assert first["country"] == "United States"
        assert first["dxcc"] == "291"
        assert first["mode"] == "CW"
        assert set(first.keys()) == {
            "call", "country", "dxcc", "app_qrzlog_status", "time_on", "freq", "mode"
        }
