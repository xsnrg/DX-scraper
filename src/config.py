import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATA_MAX_AGE_SECONDS = int(os.getenv("DXPEDITION_MAX_AGE_SECONDS", 3600))
    REQUEST_TIMEOUT = int(os.getenv("DXPEDITION_REQUEST_TIMEOUT", 30))
    RETRY_ATTEMPTS = int(os.getenv("DXPEDITION_RETRY_ATTEMPTS", 3))
    RETRY_DELAY_SECONDS = float(os.getenv("DXPEDITION_RETRY_DELAY_SECONDS", 1.0))
    
    DATA_SOURCES = {
        "dx_summit": {
            "enabled": os.getenv("DXPDX_SUMMIT_ENABLED", "true").lower() == "true",
            "url": "https://www.dxsummit.fi/summary/summaries.php",
            "polling_interval": 300
        },
        "dxcluster": {
            "enabled": os.getenv("DXPDX_CLUSTER_ENABLED", "true").lower() == "true",
            "url": "https://www.dxcluster.net/",
            "polling_interval": 600
        },
        "hamqsl": {
            "enabled": os.getenv("DXPDX_HAMQSL_ENABLED", "true").lower() == "true",
            "url": "https://www.hamqsl.com/sq700.php",
            "polling_interval": 900
        },
        "dxnews": {
            "enabled": os.getenv("DXPDX_NEWS_ENABLED", "true").lower() == "true",
            "url": "https://dxnews.com/rss.xml",
            "polling_interval": 3600
        }
    }
    
    @classmethod
    def get_enabled_sources(cls):
        return {k: v for k, v in cls.DATA_SOURCES.items() if v["enabled"]}
