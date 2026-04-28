import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.qrz_qso import (
    QSORecord,
    _authenticate,
    _fetch_qso_xml,
    _parse_qso_xml,
    _read_cache,
    _write_cache,
    sync_qso_data,
    QSO_CACHE_FILE,
)
from src.exceptions import QRZDataError


AUTH_OK = 'RESULT=OK&BOOKID=12345&BOOK_NAME=Test+Logbook&CALLSIGN=AB1CD&OWNER=AB1CD'
AUTH_FAIL = 'RESULT=FAIL&REASON=Invalid+key'

QSO_ADIF = (
    '<call>AB1CD</call><time_on>143000</time_on><qso_date>20240115</qso_date>'
    '<freq>14.200</freq><mode>CW</mode><rst_sent>59</rst_sent><rst_recv>59</rst_recv>'
    '<gridsquare>DM43</gridsquare><notes>test</notes><EOR>'
    '<call>XY9ZZ</call><time_on>150000</time_on><qso_date>20240115</qso_date>'
    '<freq>21.060</freq><mode>SSB</mode><rst_sent>59</rst_sent><rst_recv>57</rst_recv>'
    '<gridsquare>EN31</gridsquare><notes>DXpedition</notes><EOR>'
)

FETCH_OK = f'RESULT=OK&COUNT=2&ADIF={QSO_ADIF}'
FETCH_EMPTY = 'RESULT=OK&COUNT=0&ADIF='
FETCH_FAIL = 'RESULT=FAIL&COUNT=1&REASON=Bad+key'


class TestQSORecord:
    def test_from_xml_defaults(self):
        rec = QSORecord(call='AB1CD', time_on='2024-01-01T00:00:00Z')
        assert rec.call == 'AB1CD'
        assert rec.time_on == '2024-01-01T00:00:00Z'
        assert rec.time_off == ''
        assert rec.freq == ''
        assert rec.mode == ''
        assert rec.rst_sent == ''
        assert rec.rst_recv == ''
        assert rec.grid == ''
        assert rec.notes == ''

    def test_to_dict(self):
        rec = QSORecord(call='AB1CD', time_on='2024-01-01T00:00:00Z', freq='14.200', mode='CW')
        d = rec.to_dict()
        assert d['call'] == 'AB1CD'
        assert d['time_on'] == '2024-01-01T00:00:00Z'
        assert d['freq'] == '14.200'
        assert d['mode'] == 'CW'

    def test_from_dict_roundtrip(self):
        d = {'call': 'AB1CD', 'time_on': '2024-01-01T00:00:00Z', 'freq': '14.200', 'mode': 'CW',
             'time_off': '', 'rst_sent': '59', 'rst_recv': '59', 'grid': 'DM43', 'notes': ''}
        rec = QSORecord.from_dict(d)
        assert rec.to_dict() == d


class TestParseQSOXML:
    def test_parse_two_qsos(self):
        records = _parse_qso_xml(QSO_ADIF)
        assert len(records) == 2
        assert records[0].call == 'AB1CD'
        assert records[0].freq == '14.200'
        assert records[0].mode == 'CW'
        assert records[0].time_on == '2024-01-15T14:30:00'
        assert records[1].call == 'XY9ZZ'
        assert records[1].mode == 'SSB'

    def test_parse_empty(self):
        records = _parse_qso_xml('')
        assert len(records) == 0

    def test_parse_no_call(self):
        records = _parse_qso_xml('<time_on>120000</time_on><EOR>')
        assert len(records) == 0

    def test_parse_url_encoded_adif(self):
        encoded = '%3Ccall%3EAB1CD%3Ccall%3E%3Ctime_on%3E143000%3Ctime_on%3E%3Cqso_date%3E20240115%3Cqso_date%3E%3Cfreq%3E14.200%3Cfreq%3E%3Cmode%3ECW%3Cmode%3E%3Cgridsquare%3EDM43%3Cgridsquare%3E%3CEOR%3E'
        import urllib.parse
        decoded = urllib.parse.unquote(encoded)
        records = _parse_qso_xml(decoded)
        assert len(records) == 1
        assert records[0].call == 'AB1CD'
        assert records[0].freq == '14.200'
        assert records[0].mode == 'CW'
        assert records[0].time_on == '2024-01-15T14:30:00'

    def test_parse_adif_with_length_tags(self):
        adif = '<call:5>AB1CD<time_on:6>143000<qso_date:8>20240115<freq:7>14.20000<mode:3>CW<EOR>'
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        assert records[0].call == 'AB1CD'
        assert records[0].freq == '14.20000'
        assert records[0].mode == 'CW'
        assert records[0].time_on == '2024-01-15T14:30:00'

    def test_parse_adif_mixed_tag_formats(self):
        adif = '<call:5>AB1CD<time_on>143000</time_on><qso_date:8>20240115<EOR>'
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        assert records[0].call == 'AB1CD'
        assert records[0].time_on == '2024-01-15T14:30:00'

    def test_parse_adif_with_newlines(self):
        adif = '<call>AB1CD</call>\n<time_on>143000</time_on>\n<qso_date>20240115</qso_date>\n<EOR>'
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        assert records[0].call == 'AB1CD'
        assert records[0].time_on == '2024-01-15T14:30:00'

    def test_parse_adif_with_whitespace(self):
        adif = '  <call>  AB1CD  </call>  <time_on>143000</time_on><qso_date>20240115</qso_date><EOR>  '
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        assert records[0].call == 'AB1CD'
        assert records[0].time_on == '2024-01-15T14:30:00'

    def test_parse_adif_uppercase_tags(self):
        adif = '<CALL>AB1CD</CALL><TIME_ON>143000</TIME_ON><QSO_DATE>20240115</QSO_DATE><EOR>'
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        assert records[0].call == 'AB1CD'
        assert records[0].time_on == '2024-01-15T14:30:00'

    def test_parse_adif_missing_time_on(self):
        adif = '<call>AB1CD</call><qso_date>20240115</qso_date><EOR>'
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        assert records[0].call == 'AB1CD'
        assert records[0].time_on == ''

    def test_parse_adif_missing_qso_date(self):
        adif = '<call>AB1CD</call><time_on>143000</time_on><EOR>'
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        assert records[0].call == 'AB1CD'
        assert records[0].time_on == '143000'

    def test_parse_adif_no_trailing_eor(self):
        adif = '<call>AB1CD</call><time_on>143000</time_on><qso_date>20240115</qso_date>'
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        assert records[0].call == 'AB1CD'
        assert records[0].time_on == '2024-01-15T14:30:00'

    def test_parse_adif_all_fields(self):
        adif = (
            '<call>AB1CD</call><time_on>143000</time_on><time_off>144500</time_off>'
            '<qso_date>20240115</qso_date><freq>14.200</freq><mode>CW</mode>'
            '<rst_sent>59</rst_sent><rst_recv>59</rst_recv><gridsquare>DM4321</gridsquare>'
            '<notes>DXpedition test</notes><EOR>'
        )
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        r = records[0]
        assert r.call == 'AB1CD'
        assert r.time_on == '2024-01-15T14:30:00'
        assert r.time_off == '144500'
        assert r.freq == '14.200'
        assert r.mode == 'CW'
        assert r.rst_sent == '59'
        assert r.rst_recv == '59'
        assert r.grid == 'DM4321'
        assert r.notes == 'DXpedition test'

    def test_parse_adif_special_chars_in_value(self):
        adif = '<call>AB1/CD</call><time_on>143000</time_on><qso_date>20240115</qso_date><notes>Test &amp; more</notes><EOR>'
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        assert records[0].call == 'AB1/CD'
        assert records[0].notes == 'Test &amp; more'

    def test_parse_adif_multiple_qsos_with_gaps(self):
        adif = (
            '<call>AB1CD</call><time_on>143000</time_on><qso_date>20240115</qso_date><EOR>'
            '<call>XY9ZZ</call><time_on>150000</time_on><qso_date>20240115</qso_date><EOR>'
            '<call>ZL1ABC</call><time_on>160000</time_on><qso_date>20240115</qso_date><EOR>'
        )
        records = _parse_qso_xml(adif)
        assert len(records) == 3
        assert records[0].call == 'AB1CD'
        assert records[1].call == 'XY9ZZ'
        assert records[2].call == 'ZL1ABC'

    def test_parse_adif_only_eor_markers(self):
        records = _parse_qso_xml('<EOR><EOR><EOR>')
        assert len(records) == 0

    def test_parse_adif_partial_date_format(self):
        adif = '<call>AB1CD</call><time_on>143000</time_on><qso_date>240115</qso_date><EOR>'
        records = _parse_qso_xml(adif)
        assert len(records) == 1
        assert records[0].time_on == '2024-01-15T14:30:00'


class TestFetchURLDecoding:
    @pytest.mark.asyncio
    async def test_fetch_returns_url_encoded_adif(self):
        encoded_adif = '%3Ccall%3EAB1CD%3Ccall%3E%3Ctime_on%3E143000%3Ctime_on%3E%3Cqso_date%3E20240115%3Cqso_date%3E%3CEOR%3E'
        fetch_response = f'RESULT=OK&COUNT=1&ADIF={encoded_adif}'

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=fetch_response.encode())
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            adif = await _fetch_qso_xml('testtoken')
            assert '<call>' in adif
            assert 'AB1CD' in adif
            assert '%3C' not in adif


class TestNonUTF8Handling:
    @pytest.mark.asyncio
    async def test_auth_with_non_utf8_bytes(self):
        mixed = b'RESULT=OK&BOOKID=12345\xff\xfe'
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=mixed)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            token = await _authenticate('AB1CD', 'testtoken')
            assert token == 'testtoken'

    @pytest.mark.asyncio
    async def test_fetch_with_non_utf8_bytes(self):
        mixed = b'RESULT=OK&COUNT=1&ADIF=' + b'\xff\xfe'
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=mixed)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            adif = await _fetch_qso_xml('testtoken')
            assert '\ufffd' in adif or adif == ''


class TestCache:
    @pytest.fixture
    def tmp_cache_file(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "dxscraper_qso.jsonl"
        monkeypatch.setattr('src.qrz_qso.QSO_CACHE_FILE', cache_file)
        return cache_file

    def test_write_cache_full(self, tmp_cache_file):
        rec1 = QSORecord(call='AB1CD', time_on='2024-01-01T00:00:00Z')
        rec2 = QSORecord(call='XY9ZZ', time_on='2024-01-02T00:00:00Z')
        _write_cache([rec1, rec2], is_full=True)
        lines = tmp_cache_file.read_text().splitlines()
        assert len(lines) == 2
        d1 = json.loads(lines[0])
        assert d1['call'] == 'AB1CD'

    def test_write_cache_append(self, tmp_cache_file):
        rec1 = QSORecord(call='AB1CD', time_on='2024-01-01T00:00:00Z')
        _write_cache([rec1], is_full=True)
        rec2 = QSORecord(call='XY9ZZ', time_on='2024-01-02T00:00:00Z')
        _write_cache([rec2], is_full=False)
        lines = tmp_cache_file.read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[1])['call'] == 'XY9ZZ'

    def test_read_cache_empty(self, tmp_cache_file):
        tmp_cache_file.write_text('')
        records = _read_cache()
        assert records == []

    def test_read_cache_valid(self, tmp_cache_file):
        rec1 = QSORecord(call='AB1CD', time_on='2024-01-01T00:00:00Z')
        _write_cache([rec1], is_full=True)
        records = _read_cache()
        assert len(records) == 1
        assert records[0].call == 'AB1CD'

    def test_read_cache_skips_invalid(self, tmp_cache_file):
        tmp_cache_file.write_text('{"call":"AB1CD"}\ninvalid json\n{"call":"XY9ZZ"}\n')
        records = _read_cache()
        assert len(records) == 2
        assert records[0].call == 'AB1CD'
        assert records[1].call == 'XY9ZZ'


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_auth_success(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=AUTH_OK.encode())
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            token = await _authenticate('AB1CD', 'testtoken')
            assert token == 'testtoken'

    @pytest.mark.asyncio
    async def test_auth_failure(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=AUTH_FAIL.encode())
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(QRZDataError) as exc_info:
                await _authenticate('AB1CD', 'badtoken')
            assert 'FAIL' in str(exc_info.value)


class TestFetchQSOXML:
    @pytest.mark.asyncio
    async def test_fetch_success(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=FETCH_OK.encode())
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            adif = await _fetch_qso_xml('testtoken')
            assert 'AB1CD' in adif

    @pytest.mark.asyncio
    async def test_fetch_with_time_on_after(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=FETCH_OK.encode())
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            await _fetch_qso_xml('testtoken', time_on_after='2024-01-15T14:00:00Z')
            call_args = mock_session.post.call_args
            body = call_args.kwargs['data']
            assert 'MODSINCE:2024-01-15' in body

    @pytest.mark.asyncio
    async def test_fetch_failure(self):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=FETCH_FAIL.encode())
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(QRZDataError):
                await _fetch_qso_xml('testtoken')


class TestSyncQSOData:
    @pytest.fixture
    def mock_cache(self, tmp_path, monkeypatch):
        cache_file = tmp_path / "dxscraper_qso.jsonl"
        monkeypatch.setattr('src.qrz_qso.QSO_CACHE_FILE', cache_file)
        return cache_file

    def _make_mock_session(self, responses):
        """Create a properly configured mock aiohttp session.
        
        responses: list of URL-encoded response strings to return for each HTTP call.
        sync_qso_data makes 2 calls (auth + fetch), so pass 2 responses.
        """
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(side_effect=[r.encode() for r in responses])
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        return mock_session

    @pytest.mark.asyncio
    async def test_full_download_no_cache(self, mock_cache):
        mock_session = self._make_mock_session([AUTH_OK, FETCH_OK])

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await sync_qso_data('AB1CD', 'testtoken')
            assert result['status'] == 'ok'
            assert result['total_qsos'] == 2
            assert result['synced_count'] == 2
            assert mock_cache.exists()

    @pytest.mark.asyncio
    async def test_delta_sync(self, mock_cache):
        existing_rec = QSORecord(call='AB1CD', time_on='2024-01-15T10:00:00Z')
        _write_cache([existing_rec], is_full=True)

        delta_adif = (
            '<call>XY9ZZ</call><time_on>150000</time_on><qso_date>20240115</qso_date>'
            '<freq>21.060</freq><mode>SSB</mode><rst_sent>59</rst_sent><rst_recv>57</rst_recv>'
            '<gridsquare>EN31</gridsquare><notes></notes><EOR>'
        )
        delta_fetch = f'RESULT=OK&COUNT=1&ADIF={delta_adif}'

        mock_session = self._make_mock_session([AUTH_OK, delta_fetch])

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await sync_qso_data('AB1CD', 'testtoken')
            assert result['status'] == 'ok'
            assert result['total_qsos'] == 2
            assert result['synced_count'] == 1

            lines = mock_cache.read_text().splitlines()
            assert len(lines) == 2
            assert json.loads(lines[0])['call'] == 'AB1CD'
            assert json.loads(lines[1])['call'] == 'XY9ZZ'

    @pytest.mark.asyncio
    async def test_no_creds(self, mock_cache):
        result = await sync_qso_data('', '')
        assert result['status'] == 'error'
        assert 'required' in result['error']

    @pytest.mark.asyncio
    async def test_auth_failure(self, mock_cache):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=AUTH_FAIL.encode())
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await sync_qso_data('AB1CD', 'badtoken')
            assert result['status'] == 'error'
            assert 'FAIL' in result['error']

    @pytest.mark.asyncio
    async def test_empty_cache_re_download(self, mock_cache):
        mock_cache.write_text('invalid json\n')

        mock_session = self._make_mock_session([AUTH_OK, FETCH_OK])

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await sync_qso_data('AB1CD', 'testtoken')
            assert result['status'] == 'ok'
            assert result['total_qsos'] == 2
            assert result['synced_count'] == 2

    @pytest.mark.asyncio
    async def test_delta_no_new_records(self, mock_cache):
        existing_rec = QSORecord(call='AB1CD', time_on='2024-01-15T10:00:00Z')
        _write_cache([existing_rec], is_full=True)

        mock_session = self._make_mock_session([AUTH_OK, FETCH_EMPTY])

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await sync_qso_data('AB1CD', 'testtoken')
            assert result['status'] == 'ok'
            assert result['total_qsos'] == 1
            assert result['synced_count'] == 0
