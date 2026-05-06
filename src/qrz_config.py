import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Optional

import keyring
import keyring.errors as keyring_errors

_CONFIG_DIR = Path.home() / ".config" / "dxscraper"
_CONFIG_FILE = _CONFIG_DIR / "dxscraper_config.json"
_KEYRING_SERVICE = "dxscraper"
_KEYRING_USER = "qrz_token"


class QRZConfigError(Exception):
    """Error reading or writing QRZ config"""
    pass


class QRZKeyringError(QRZConfigError):
    """Error accessing the system keyring"""
    pass


def _ensure_config_dir():
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(str(_CONFIG_DIR), stat.S_IRWXU)  # 0o700


def _ensure_config_file():
    if not _CONFIG_FILE.exists():
        _ensure_config_dir()
        _CONFIG_FILE.write_text("{}")
        os.chmod(str(_CONFIG_FILE), stat.S_IRUSR | stat.S_IWUSR)  # 0o600


def _atomic_write_config(data: dict):
    """Write config atomically to avoid corruption on crash."""
    _ensure_config_dir()
    target_dir = str(_CONFIG_FILE.parent)
    fd, tmp_path = tempfile.mkstemp(dir=target_dir, suffix=".tmp")
    try:
        content = json.dumps(data, indent=2)
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
        os.close(fd)
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_path, str(_CONFIG_FILE))
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _safe_keyring_get() -> Optional[str]:
    """Read token from keyring, returning None on any keyring error."""
    try:
        return keyring.get_password(_KEYRING_SERVICE, _KEYRING_USER)
    except keyring_errors.NoKeyringError as e:
        raise QRZKeyringError(f"No keyring backend available: {e}")
    except keyring_errors.InitError as e:
        raise QRZKeyringError(f"Keyring backend failed to initialize: {e}")
    except Exception as e:
        raise QRZKeyringError(f"Keyring read error: {e}")


def _safe_keyring_set(token: str):
    """Write token to keyring, wrapping errors."""
    try:
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USER, token)
    except keyring_errors.NoKeyringError as e:
        raise QRZKeyringError(f"No keyring backend available: {e}")
    except keyring_errors.InitError as e:
        raise QRZKeyringError(f"Keyring backend failed to initialize: {e}")
    except Exception as e:
        raise QRZKeyringError(f"Keyring write error: {e}")


def get_qrz_data() -> dict:
    _ensure_config_file()
    try:
        data = json.loads(_CONFIG_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}

    try:
        token = _safe_keyring_get()
    except QRZKeyringError:
        data["keyring_unavailable"] = True
        data["token"] = ""
        return data

    data["token"] = token or ""
    return data


def save_qrz_data(callsign: str, token: str):
    if not callsign or not token:
        raise QRZConfigError("callsign and token must not be empty")

    data = get_qrz_data()
    data["callsign"] = callsign.strip()
    data.pop("token", None)

    try:
        _atomic_write_config(data)
    except Exception as e:
        raise QRZConfigError(f"Failed to write config file: {e}")

    try:
        _safe_keyring_set(token.strip())
    except QRZKeyringError as e:
        raise QRZConfigError(
            f"Config file saved but token could not be stored in keyring: {e}"
        )
