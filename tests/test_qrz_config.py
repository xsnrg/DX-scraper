"""Unit tests for QRZ config file + keyring handling."""
import json
import os
from unittest.mock import patch

import keyring.errors as keyring_errors
import pytest

from src.qrz_config import (
    QRZConfigError,
    QRZKeyringError,
    get_last_sync,
    get_qrz_data,
    save_last_sync,
    save_qrz_data,
)


def _chmod_modes(mock_chmod):
    """Permission bits passed to os.chmod, masked to the POSIX mode."""
    return [c.args[1] & 0o777 for c in mock_chmod.call_args_list]


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "dxscraper"
    config_dir.mkdir()
    config_file = config_dir / "dxscraper_config.json"
    monkeypatch.setattr("src.qrz_config._CONFIG_DIR", config_dir)
    monkeypatch.setattr("src.qrz_config._CONFIG_FILE", config_file)
    return config_dir, config_file


class TestSaveQrzData:
    def test_rejects_empty_callsign(self, isolated_config):
        with pytest.raises(QRZConfigError, match="must not be empty"):
            save_qrz_data("", "token")

    def test_rejects_empty_token(self, isolated_config):
        with pytest.raises(QRZConfigError, match="must not be empty"):
            save_qrz_data("W1AW", "")

    def test_rejects_both_empty(self, isolated_config):
        with pytest.raises(QRZConfigError):
            save_qrz_data("", "")

    def test_token_not_written_to_json(self, isolated_config):
        _dir, config_file = isolated_config
        with patch("src.qrz_config.keyring.get_password", return_value="secret"), \
             patch("src.qrz_config.keyring.set_password") as mock_set:
            save_qrz_data(" W1AW ", " secret-token ")

        data = json.loads(config_file.read_text())
        assert data["callsign"] == "W1AW"
        assert "token" not in data
        mock_set.assert_called_once()
        assert mock_set.call_args[0][2] == "secret-token"

    def test_config_file_mode_is_600(self, isolated_config):
        _dir, config_file = isolated_config
        with patch("src.qrz_config.keyring.get_password", return_value=None), \
             patch("src.qrz_config.keyring.set_password"), \
             patch("src.qrz_config.os.chmod", wraps=os.chmod) as mock_chmod:
            save_qrz_data("W1AW", "token")
        assert config_file.is_file()
        assert os.access(config_file, os.R_OK | os.W_OK)
        assert 0o600 in _chmod_modes(mock_chmod)
        if os.name != "nt":
            assert config_file.stat().st_mode & 0o777 == 0o600

    def test_config_dir_mode_is_700(self, isolated_config):
        config_dir, _file = isolated_config
        with patch("src.qrz_config.keyring.get_password", return_value=None), \
             patch("src.qrz_config.keyring.set_password"), \
             patch("src.qrz_config.os.chmod", wraps=os.chmod) as mock_chmod:
            save_qrz_data("W1AW", "token")
        assert config_dir.is_dir()
        assert os.access(config_dir, os.R_OK | os.W_OK | os.X_OK)
        assert 0o700 in _chmod_modes(mock_chmod)
        if os.name != "nt":
            assert config_dir.stat().st_mode & 0o777 == 0o700

    def test_keyring_write_failure_raises_after_file_save(self, isolated_config):
        _dir, config_file = isolated_config
        with patch("src.qrz_config.keyring.get_password", return_value=None), \
             patch(
                 "src.qrz_config.keyring.set_password",
                 side_effect=keyring_errors.NoKeyringError("no backend"),
             ):
            with pytest.raises(QRZConfigError, match="keyring"):
                save_qrz_data("W1AW", "token")
        data = json.loads(config_file.read_text())
        assert data["callsign"] == "W1AW"


class TestGetQrzData:
    def test_returns_token_from_keyring(self, isolated_config):
        _dir, config_file = isolated_config
        config_file.write_text(json.dumps({"callsign": "W1AW"}))
        with patch("src.qrz_config.keyring.get_password", return_value="abc123"):
            data = get_qrz_data()
        assert data["callsign"] == "W1AW"
        assert data["token"] == "abc123"
        assert data.get("keyring_unavailable") is not True

    def test_keyring_unavailable_flag(self, isolated_config):
        with patch(
            "src.qrz_config.keyring.get_password",
            side_effect=keyring_errors.NoKeyringError("no backend"),
        ):
            data = get_qrz_data()
        assert data["keyring_unavailable"] is True
        assert data["token"] == ""

    def test_keyring_init_error_sets_flag(self, isolated_config):
        with patch(
            "src.qrz_config.keyring.get_password",
            side_effect=keyring_errors.InitError("init failed"),
        ):
            data = get_qrz_data()
        assert data["keyring_unavailable"] is True
        assert data["token"] == ""

    def test_generic_keyring_error_sets_flag(self, isolated_config):
        with patch(
            "src.qrz_config.keyring.get_password",
            side_effect=RuntimeError("boom"),
        ):
            data = get_qrz_data()
        assert data["keyring_unavailable"] is True

    def test_corrupt_json_recovers(self, isolated_config):
        _dir, config_file = isolated_config
        config_file.write_text("{not json")
        with patch("src.qrz_config.keyring.get_password", return_value="tok"):
            data = get_qrz_data()
        assert data["token"] == "tok"
        assert "callsign" not in data or data.get("callsign") in (None, "")

    def test_missing_file_creates_empty_config(self, isolated_config):
        _dir, config_file = isolated_config
        assert not config_file.exists()
        with patch("src.qrz_config.keyring.get_password", return_value=None):
            data = get_qrz_data()
        assert config_file.exists()
        assert data["token"] == ""


class TestAtomicWrite:
    def test_tmp_cleaned_on_replace_error(self, isolated_config):
        config_dir, config_file = isolated_config
        with patch("src.qrz_config.keyring.get_password", return_value=None), \
             patch("src.qrz_config.keyring.set_password"), \
             patch("src.qrz_config.os.replace", side_effect=OSError("disk full")):
            with pytest.raises(QRZConfigError, match="Failed to write config"):
                save_qrz_data("W1AW", "token")
        leftovers = list(config_dir.glob("*.tmp"))
        assert leftovers == []


class TestLastSync:
    def test_missing_returns_none(self, isolated_config):
        assert get_last_sync() is None

    def test_corrupt_json_returns_none(self, isolated_config):
        _dir, config_file = isolated_config
        config_file.write_text("{bad")
        assert get_last_sync() is None

    def test_roundtrip(self, isolated_config):
        with patch("src.qrz_config.keyring.get_password", return_value=None), \
             patch("src.qrz_config.keyring.set_password"):
            save_qrz_data("W1AW", "token")
            save_last_sync("2024-01-15T12:00:00+00:00")
        assert get_last_sync() == "2024-01-15T12:00:00+00:00"
        data = json.loads(isolated_config[1].read_text())
        assert data["callsign"] == "W1AW"

    def test_save_last_sync_write_error(self, isolated_config):
        with patch("src.qrz_config.keyring.get_password", return_value=None), \
             patch("src.qrz_config.os.replace", side_effect=OSError("disk")):
            with pytest.raises(QRZConfigError, match="last_sync"):
                save_last_sync("2024-01-01T00:00:00+00:00")


class TestExceptionHierarchy:
    def test_keyring_error_is_config_error(self):
        assert issubclass(QRZKeyringError, QRZConfigError)
        err = QRZKeyringError("no backend")
        assert "no backend" in str(err)
