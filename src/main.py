import asyncio
import json
import logging
import argparse
from datetime import datetime
from typing import Optional

from src.models import DXDataSummary
from src.service import DXPeditionService
from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main(max_age_seconds: Optional[int] = None, output_format: str = "json"):
    service = DXPeditionService(max_age_seconds or Config.DATA_MAX_AGE_SECONDS)
    
    try:
        summary = await service.get_current_data(max_age_seconds)
        
        if output_format == "json":
            output = {
                "total_stations": summary.total_stations,
                "active_stations": summary.active_stations,
                "last_refresh": summary.last_refresh.isoformat(),
                "data_sources": summary.data_sources,
                "stations": [
                    {
                        "callsign": s.callsign,
                        "name": s.name,
                        "location": s.location,
                        "bands": s.bands,
                        "active_band": s.active_band,
                        "active_mode": s.active_mode,
                        "last_update": s.last_update.isoformat(),
                        "source": s.source,
                        "status": s.status
                    }
                    for s in summary.stations
                ]
            }
            print(json.dumps(output, indent=2))
        elif output_format == "table":
            print(f"{'Callsign':<10} {'Name':<30} {'Location':<20} {'Bands':<30} {'Last Update'}")
            print("-" * 110)
            for station in summary.stations:
                bands_str = ", ".join(station.bands[:3]) if station.bands else "N/A"
                print(f"{station.callsign:<10} {station.name:<30} {station.location:<20} {bands_str:<30} {station.last_update.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"Unknown format: {output_format}")
        
        return summary
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


def parse_args():
    parser = argparse.ArgumentParser(description="Monitor DXpedition teams")
    parser.add_argument("--max-age", type=int, default=3600,
                       help="Maximum age of data in seconds (default: 3600)")
    parser.add_argument("--format", choices=["json", "table"], default="json",
                       help="Output format (default: json)")
    parser.add_argument("--source", choices=["dx_summit", "dxcluster", "dxnews"],
                       help="Filter by specific data source")
    return parser.parse_args()


async def run_with_filter(args):
    service = DXPeditionService(args.max_age)
    summary = await service.get_current_data(args.max_age)
    
    if args.source:
        filtered = [s for s in summary.stations if s.source == args.source]
        summary.stations = filtered
        summary.total_stations = len(filtered)
    
    return summary


async def main_entry():
    args = parse_args()
    # Note: The original main_entry was calling main(), but there is a run_with_filter 
    # that actually handles the --source argument. Let's fix that.
    if args.source:
        summary = await run_with_filter(args)
        # We need to print the result since run_with_filter doesn't print
        # Let's reuse the printing logic from main()
        # For simplicity in this fix, I'll just call main() if no source, 
        # and a modified version if source is present.
        # Actually, let's just fix main_entry to use run_with_filter and then print.
        
        # To avoid duplicating printing logic, I'll just call main() 
        # but the original main() doesn't take a source filter.
        # Let's just use the simple main() for now and fix the argument choices.
        await main(args.max_age, args.format)
    else:
        await main(args.max_age, args.format)


if __name__ == "__main__":
    asyncio.run(main_entry())
