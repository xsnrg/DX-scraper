import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATA_MAX_AGE_SECONDS = int(os.getenv("DXPEDITION_MAX_AGE_SECONDS", 3600))
    REQUEST_TIMEOUT = int(os.getenv("DXPEDITION_REQUEST_TIMEOUT", 30))
    RETRY_ATTEMPTS = int(os.getenv("DXPEDITION_RETRY_ATTEMPTS", 3))
    RETRY_DELAY_SECONDS = float(os.getenv("DXPEDITION_RETRY_DELAY_SECONDS", 1.0))
    
    DATA_SOURCES = {
        "dx_cluster": "DX Cluster",
        "dx_news": "DX News",
        "dx_summit": "DX Summit",
        "hamqth": "HamQTH DX Cluster",
    }
    @classmethod
    def get_enabled_sources(cls):
        return {k: v for k, v in cls.DATA_SOURCES.items() if v["enabled"]}

