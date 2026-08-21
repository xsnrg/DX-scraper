"""Unit tests for Config defaults and enabled-source filtering."""
from src.config import Config


class TestConfigDefaults:
    def test_timeout_retry_age_defaults(self):
        assert Config.DATA_MAX_AGE_SECONDS == 3600
        assert Config.REQUEST_TIMEOUT == 30
        assert Config.RETRY_ATTEMPTS == 3
        assert Config.RETRY_DELAY_SECONDS == 1.0

    def test_all_known_sources_present(self):
        assert set(Config.DATA_SOURCES.keys()) == {
            "dx_cluster",
            "dx_news",
            "dx_summit",
            "hamqth",
            "pota",
            "ng3k",
        }

    def test_sources_have_name_and_enabled(self):
        for key, meta in Config.DATA_SOURCES.items():
            assert "name" in meta, f"{key} missing name"
            assert "enabled" in meta, f"{key} missing enabled"
            assert isinstance(meta["enabled"], bool)


class TestGetEnabledSources:
    def test_all_enabled_by_default(self):
        enabled = Config.get_enabled_sources()
        assert set(enabled.keys()) == set(Config.DATA_SOURCES.keys())

    def test_filters_disabled_sources(self, monkeypatch):
        sources = {
            "dx_cluster": {"name": "Spothole", "enabled": True},
            "dx_news": {"name": "DX News", "enabled": False},
            "dx_summit": {"name": "DX Summit", "enabled": True},
            "hamqth": {"name": "HamQTH", "enabled": False},
            "pota": {"name": "POTA", "enabled": True},
        }
        monkeypatch.setattr(Config, "DATA_SOURCES", sources)
        enabled = Config.get_enabled_sources()
        assert set(enabled.keys()) == {"dx_cluster", "dx_summit", "pota"}
        assert "dx_news" not in enabled
        assert "hamqth" not in enabled

    def test_all_disabled_returns_empty(self, monkeypatch):
        sources = {k: {**v, "enabled": False} for k, v in Config.DATA_SOURCES.items()}
        monkeypatch.setattr(Config, "DATA_SOURCES", sources)
        assert Config.get_enabled_sources() == {}
