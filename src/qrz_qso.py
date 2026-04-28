import asyncio
import html
import json
import logging
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from .exceptions import QRZDataError
from .qrz_config import _CONFIG_DIR

logger = logging.getLogger(__name__)

LOGBOOK_API_URL = "https://logbook.qrz.com/api"
AGENT = "W6GRE-DXScraper/1.0"
QSO_CACHE_FILE = _CONFIG_DIR / "dxscraper_qso.jsonl"
LOG_FILE = _CONFIG_DIR / "dxscraper.log"


def _setup_logging():
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    fh = logging.FileHandler(str(LOG_FILE), encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    root.addHandler(sh)


_setup_logging()


class QSORecord:
    __slots__ = ['call', 'time_on', 'time_off', 'freq', 'mode', 'rst_sent', 'rst_recv', 'grid', 'notes']

    def __init__(self, call: str, time_on: str, time_off: str = "", freq: str = "",
                 mode: str = "", rst_sent: str = "", rst_recv: str = "", grid: str = "", notes: str = ""):
        self.call = call
        self.time_on = time_on
        self.time_off = time_off
        self.freq = freq
        self.mode = mode
        self.rst_sent = rst_sent
        self.rst_recv = rst_recv
        self.grid = grid
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            'call': self.call,
            'time_on': self.time_on,
            'time_off': self.time_off,
            'freq': self.freq,
            'mode': self.mode,
            'rst_sent': self.rst_sent,
            'rst_recv': self.rst_recv,
            'grid': self.grid,
            'notes': self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'QSORecord':
        return cls(
            call=d.get('call', ''),
            time_on=d.get('time_on', ''),
            time_off=d.get('time_off', ''),
            freq=d.get('freq', ''),
            mode=d.get('mode', ''),
            rst_sent=d.get('rst_sent', ''),
            rst_recv=d.get('rst_recv', ''),
            grid=d.get('grid', ''),
            notes=d.get('notes', ''),
        )

    @classmethod
    def from_xml(cls, elem) -> 'QSORecord':
        return cls(
            call=elem.findtext('call', ''),
            time_on=elem.findtext('time_on', ''),
            time_off=elem.findtext('time_off', ''),
            freq=elem.findtext('freq', ''),
            mode=elem.findtext('mode', ''),
            rst_sent=elem.findtext('rst_sent', ''),
            rst_recv=elem.findtext('rst_recv', ''),
            grid=elem.findtext('grid', ''),
            notes=elem.findtext('notes', ''),
        )


async def _authenticate(callsign: str, token: str) -> str:
    import urllib.parse
    import aiohttp
    params = urllib.parse.urlencode({
        'KEY': token,
        'ACTION': 'STATUS',
        'CALLSIGN': callsign,
    })
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': AGENT,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(LOGBOOK_API_URL, data=params, headers=headers, timeout=30) as resp:
                raw = await resp.read()
                text = raw.decode('utf-8', errors='replace')
                logger.debug(f"Auth response: status={resp.status}, body={text[:500]}")
                if resp.status != 200:
                    raise QRZDataError(f"Auth HTTP error: status={resp.status}, body={text[:200]}")
                result = {}
                for part in text.split('&'):
                    if '=' in part:
                        k, v = part.split('=', 1)
                        result[k] = v
                if result.get('RESULT') != 'OK':
                    reason = result.get('REASON', 'unknown')
                    logger.error(f"Auth failed: RESULT={result.get('RESULT')}, REASON={reason}, full_response={text[:500]}")
                    raise QRZDataError(f"Auth failed: RESULT={result.get('RESULT', 'unknown')} (REASON={reason})")
                session_token = result.get('SESSIONTOKEN', token)
                return session_token
    except QRZDataError:
        raise
    except Exception as e:
        raise QRZDataError(f"Auth request failed: {e}")


async def _fetch_qso_xml(session_token: str, time_on_after: Optional[str] = None, callsign: str = "") -> str:
    import urllib.parse
    import aiohttp
    params = {
        'KEY': session_token,
        'ACTION': 'FETCH',
        'OPTION': 'ALL',
        'TYPE': 'ADIF',
    }
    if time_on_after:
        params['OPTION'] = f'MODSINCE:{time_on_after[:10]}'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': AGENT,
    }
    try:
        async with aiohttp.ClientSession() as session:
            # Build query string manually to preserve colons in OPTION values
            # QRZ API uses colon-separated name:value pairs in OPTION (e.g., MODSINCE:2023-01-01)
            # urllib.parse.urlencode encodes colons to %3A which QRZ doesn't decode
            parts = [f"KEY={session_token}", f"ACTION=FETCH", f"TYPE=ADIF"]
            if callsign:
                parts.append(f"CALLSIGN={callsign}")
            if time_on_after:
                parts.append(f"OPTION=MODSINCE:{time_on_after[:10]}")
            else:
                parts.append("OPTION=ALL")
            encoded = "&".join(parts)
            logger.info(f"Fetch request: {encoded}")
            async with session.post(LOGBOOK_API_URL, data=encoded, headers=headers, timeout=60) as resp:
                raw = await resp.read()
                text = raw.decode('utf-8', errors='replace')
                logger.debug(f"Fetch response: status={resp.status}, body={text[:500]}")
                
                result = {}
                for part in text.split('&'):
                    if '=' in part:
                        k, v = part.split('=', 1)
                        result[k] = v
                
                if result.get('RESULT') != 'OK':
                    reason = result.get('REASON', 'unknown')
                    count = result.get('COUNT', '0')
                    if count == '0':
                        logger.info(f"Fetch returned no results: RESULT={result.get('RESULT')}, REASON={reason}")
                        return ''
                    logger.error(f"Fetch failed: RESULT={result.get('RESULT')}, REASON={reason}, full_response={text[:500]}")
                    raise QRZDataError(f"Fetch failed: RESULT={result.get('RESULT', 'unknown')} (REASON={reason})")
                
                adif = ''
                adif_idx = text.find('ADIF=')
                if adif_idx >= 0:
                    adif = text[adif_idx + 5:]
                adif = html.unescape(urllib.parse.unquote(adif))
                return adif
    except QRZDataError:
        raise
    except Exception as e:
        raise QRZDataError(f"Fetch request failed: {e}")


def _parse_qso_xml(adif: str) -> list[QSORecord]:
    import re
    records = []
    if not adif:
        return records
    
    adif = adif.replace('\ufffd', '')
    
    # Split into individual QSO records by <eor> marker (case-insensitive)
    raw_records = re.split(r'<eor>', adif, flags=re.IGNORECASE)
    
    # Match <tag:LENGTH>value where value is exactly LENGTH chars
    tag_pattern = re.compile(r'<([a-zA-Z_][a-zA-Z0-9_]*):(\d+)>([^<]*)', re.IGNORECASE)
    # Match <tag>value</tag> format
    closing_tag_pattern = re.compile(r'<([a-zA-Z_][a-zA-Z0-9_]*)>([^<]*)</\1>', re.IGNORECASE)
    # Match <tag>value<tag> format (no slash in closing tag)
    self_closing_tag_pattern = re.compile(r'<([a-zA-Z_][a-zA-Z0-9_]*)>([^<]*)(?=<\1>)', re.IGNORECASE)
    
    for raw in raw_records:
        if not raw.strip():
            continue
        
        record = QSORecord(call='', time_on='')
        qso_date = None
        
        for match in tag_pattern.finditer(raw):
            field_name = match.group(1).lower()
            value = match.group(3).strip()
            
            if field_name == 'call':
                record.call = value
            elif field_name == 'time_on':
                record.time_on = value
            elif field_name == 'time_off':
                record.time_off = value
            elif field_name == 'freq':
                record.freq = value
            elif field_name == 'mode':
                record.mode = value
            elif field_name == 'rst_sent':
                record.rst_sent = value
            elif field_name == 'rst_recv':
                record.rst_recv = value
            elif field_name == 'gridsquare':
                record.grid = value
            elif field_name == 'notes':
                record.notes = value
            elif field_name == 'qso_date':
                qso_date = value
        
        for match in closing_tag_pattern.finditer(raw):
            field_name = match.group(1).lower()
            value = match.group(2).strip()
            
            if field_name == 'call' and not record.call:
                record.call = value
            elif field_name == 'time_on' and not record.time_on:
                record.time_on = value
            elif field_name == 'time_off' and not record.time_off:
                record.time_off = value
            elif field_name == 'freq' and not record.freq:
                record.freq = value
            elif field_name == 'mode' and not record.mode:
                record.mode = value
            elif field_name == 'rst_sent' and not record.rst_sent:
                record.rst_sent = value
            elif field_name == 'rst_recv' and not record.rst_recv:
                record.rst_recv = value
            elif field_name == 'gridsquare' and not record.grid:
                record.grid = value
            elif field_name == 'notes' and not record.notes:
                record.notes = value
            elif field_name == 'qso_date' and not qso_date:
                qso_date = value
        
        for match in self_closing_tag_pattern.finditer(raw):
            field_name = match.group(1).lower()
            value = match.group(2).strip()
            
            if field_name == 'call' and not record.call:
                record.call = value
            elif field_name == 'time_on' and not record.time_on:
                record.time_on = value
            elif field_name == 'time_off' and not record.time_off:
                record.time_off = value
            elif field_name == 'freq' and not record.freq:
                record.freq = value
            elif field_name == 'mode' and not record.mode:
                record.mode = value
            elif field_name == 'rst_sent' and not record.rst_sent:
                record.rst_sent = value
            elif field_name == 'rst_recv' and not record.rst_recv:
                record.rst_recv = value
            elif field_name == 'gridsquare' and not record.grid:
                record.grid = value
            elif field_name == 'notes' and not record.notes:
                record.notes = value
            elif field_name == 'qso_date' and not qso_date:
                qso_date = value
        
        if qso_date and record.time_on:
            if len(qso_date) >= 8:
                if record.time_on.isdigit() and len(record.time_on) == 6:
                    record.time_on = f"{qso_date[:4]}-{qso_date[4:6]}-{qso_date[6:8]}T{record.time_on[:2]}:{record.time_on[2:4]}:{record.time_on[4:6]}"
                elif record.time_on.isdigit() and len(record.time_on) == 4:
                    record.time_on = f"{qso_date[:4]}-{qso_date[4:6]}-{qso_date[6:8]}T{record.time_on[:2]}:{record.time_on[2:4]}"
                else:
                    record.time_on = f"{qso_date[:4]}-{qso_date[4:6]}-{qso_date[6:8]}T{record.time_on}"
            elif len(qso_date) == 6:
                if record.time_on.isdigit() and len(record.time_on) == 6:
                    record.time_on = f"20{qso_date[:2]}-{qso_date[2:4]}-{qso_date[4:6]}T{record.time_on[:2]}:{record.time_on[2:4]}:{record.time_on[4:6]}"
                elif record.time_on.isdigit() and len(record.time_on) == 4:
                    record.time_on = f"20{qso_date[:2]}-{qso_date[2:4]}-{qso_date[4:6]}T{record.time_on[:2]}:{record.time_on[2:4]}"
                else:
                    record.time_on = f"20{qso_date[:2]}-{qso_date[2:4]}-{qso_date[4:6]}T{record.time_on}"
        
        if record.call:
            records.append(record)
    
    return records


def _read_cache() -> list[QSORecord]:
    if not QSO_CACHE_FILE.exists():
        return []
    records = []
    for line in QSO_CACHE_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            records.append(QSORecord.from_dict(d))
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Skipping invalid cache line: {line[:80]}")
    return records


def _write_cache(records: list[QSORecord], is_full: bool = False):
    import os
    import stat
    QSO_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if is_full:
        QSO_CACHE_FILE.write_text('')
        os.chmod(str(QSO_CACHE_FILE), stat.S_IRUSR | stat.S_IWUSR)
    with open(str(QSO_CACHE_FILE), 'a') as f:
        for rec in records:
            f.write(json.dumps(rec.to_dict()) + '\n')


async def sync_qso_data(callsign: str, token: str) -> dict:
    if not callsign or not token:
        return {'status': 'error', 'error': 'callsign and token are required'}

    cache_exists = QSO_CACHE_FILE.exists()

    try:
        session_token = await _authenticate(callsign, token)
    except QRZDataError as e:
        return {'status': 'error', 'error': str(e)}

    try:
        if not cache_exists:
            xml = await _fetch_qso_xml(session_token, callsign=callsign)
            records = _parse_qso_xml(xml)
            _write_cache(records, is_full=True)
            return {'status': 'ok', 'total_qsos': len(records), 'synced_count': len(records)}
        else:
            existing = _read_cache()
            if not existing:
                xml = await _fetch_qso_xml(session_token, callsign=callsign)
                records = _parse_qso_xml(xml)
                _write_cache(records, is_full=True)
                return {'status': 'ok', 'total_qsos': len(records), 'synced_count': len(records)}

            last_time_on = existing[-1].time_on
            if not last_time_on:
                xml = await _fetch_qso_xml(session_token, callsign=callsign)
                records = _parse_qso_xml(xml)
                _write_cache(records, is_full=True)
                return {'status': 'ok', 'total_qsos': len(records), 'synced_count': len(records)}

            xml = await _fetch_qso_xml(session_token, time_on_after=last_time_on, callsign=callsign)
            records = _parse_qso_xml(xml)
            if records:
                _write_cache(records, is_full=False)
                return {'status': 'ok', 'total_qsos': len(existing) + len(records), 'synced_count': len(records)}
            return {'status': 'ok', 'total_qsos': len(existing), 'synced_count': 0}
    except QRZDataError as e:
        return {'status': 'error', 'error': str(e)}
    except Exception as e:
        return {'status': 'error', 'error': f'Unexpected error: {e}'}
