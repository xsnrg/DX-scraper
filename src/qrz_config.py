import json
import os
import stat
from pathlib import Path


_CONFIG_DIR = Path.home() / ".config" / "dxscraper"
_CONFIG_FILE = _CONFIG_DIR / "dxscraper_config.json"


def _ensure_config_dir():
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(str(_CONFIG_DIR), stat.S_IRWXU)  # 0o700


def _ensure_config_file():
    if not _CONFIG_FILE.exists():
        _ensure_config_dir()
        _CONFIG_FILE.write_text("{}")
        os.chmod(str(_CONFIG_FILE), stat.S_IRUSR | stat.S_IWUSR)  # 0o600


def get_qrz_data() -> dict:
    _ensure_config_file()
    try:
        return json.loads(_CONFIG_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_qrz_data(callsign: str, token: str):
    _ensure_config_dir()
    data = get_qrz_data()
    data["callsign"] = callsign.strip()
    data["token"] = token.strip()
    _CONFIG_FILE.write_text(json.dumps(data, indent=2))
    os.chmod(str(_CONFIG_FILE), stat.S_IRUSR | stat.S_IWUSR)  # 0o600
