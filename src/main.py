import asyncio
import json
import logging
import argparse
import sys
from datetime import datetime
from typing import Optional

from src.models import DXDataSummary
from src.service import DXPeditionService
from src.config import Config
from src.qrz_qso import sync_qso_data, LOG_FILE
from src.qrz_config import get_qrz_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main(max_age_seconds: Optional[int] = None, output_format: str = "json", source: Optional[str] = None):
    service = DXPeditionService(max_age_seconds or Config.DATA_MAX_AGE_SECONDS)
    
    try:
        summary = await service.get_current_data(max_age_seconds)
        
        if source:
            summary.stations = [s for s in summary.stations if s.source == source]
            summary.total_stations = len(summary.stations)
            summary.active_stations = len([s for s in summary.stations if s.status == "active"])
            summary.data_sources = list(set(s.source for s in summary.stations))

        if output_format == "json":
            output = {
                "total_stations": summary.total_stations,
                "active_stations": summary.active_stations,
                "last_refresh": summary.last_refresh.isoformat(),
                "data_sources": summary.data_sources,
                "stations": [
                    {
                        "callsign": s.callsign,
                        "dx_country": s.dx_country,
                        "spotter_country": s.spotter_country,
                        "spotter": s.spotter,
                        "band": s.band,
                        "frequency": s.frequency,
                        "mode": s.mode,
                        "comment": s.comment,
                        "last_update": s.last_update.isoformat(),
                        "source": s.source,
                        "status": s.status
                    }
                    for s in summary.stations
                ]
            }
            print(json.dumps(output, indent=2))
        elif output_format == "table":
            print(f"{'Callsign':<10} {'DX Country':<15} {'Spotter':<15} {'Band':<8} {'Freq':<12} {'Mode/Comment':<30} {'Updated':<20} {'Source'}")
            print("-" * 130)
            for station in summary.stations:
                freq_str = f"{station.frequency:.4f}" if station.frequency else ""
                mode_comment = f"{station.mode}" if station.mode else station.comment
                print(f"{station.callsign:<10} {station.dx_country:<15} {station.spotter:<15} {station.band:<8} {freq_str:<12} {mode_comment:<30} {station.last_update.strftime('%Y-%m-%d %H:%M'):<20} {station.source}")
        else:
            print(f"Unknown format: {output_format}")
        
        return summary
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


async def run_with_filter(args):
    service = DXPeditionService(args.max_age or Config.DATA_MAX_AGE_SECONDS)
    summary = await service.get_current_data(args.max_age)
    if args.source:
        summary.stations = [s for s in summary.stations if s.source == args.source]
        summary.total_stations = len(summary.stations)
        summary.active_stations = len([s for s in summary.stations if s.status == "active"])
        summary.data_sources = list(set(s.source for s in summary.stations))
    return summary


def parse_args():
    parser = argparse.ArgumentParser(description="Monitor DXpedition teams")
    parser.add_argument("--max-age", type=int, default=3600,
                       help="Maximum age of data in seconds (default: 3600)")
    parser.add_argument("--format", choices=["json", "table"], default="json",
                       help="Output format (default: json)")
    parser.add_argument("--source", choices=["dx_summit", "dxcluster"],
                        help="Filter by specific data source")
    parser.add_argument("--debug-qrz", action="store_true",
                        help="Test QRZ API with stored credentials and print verbose debug output")
    return parser.parse_args()


async def main_entry():
    args = parse_args()
    if args.debug_qrz:
        await _debug_qrz()
        return
    await main(args.max_age, args.format, source=args.source)


async def _debug_qrz():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    logger = logging.getLogger(__name__)
    
    data = get_qrz_data()
    callsign = data.get("callsign", "")
    token = data.get("token", "")
    
    if not callsign or not token:
        print("ERROR: No QRZ credentials found in", get_qrz_data.__module__)
        print("Store them with: python -m src.main --debug-qrz (via the web UI)")
        sys.exit(1)
    
    print(f"Callsign: {callsign}")
    print(f"Token: {token[:10]}...{token[-5:]}")
    print(f"Log file: {LOG_FILE}")
    print()
    
    print("=== Step 1: Authenticating ===")
    try:
        result = await sync_qso_data(callsign, token)
        print(f"Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
        print()
        print("=== Check log file for details: ===")
        print(f"  cat {LOG_FILE}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main_entry())

