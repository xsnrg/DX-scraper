import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from src.api import app
from src.exceptions import QRZDataError

client = TestClient(app)


class TestQRZTokenValidation:
    """Tests for token validation on POST /qrz-token."""

    def _make_mock_session(self, auth_response):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=auth_response.encode())
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        return mock_session

    def test_save_token_without_creds_returns_400(self):
        response = client.post("/qrz-token", json={"callsign": "", "token": "abc"})
        assert response.status_code == 400

        response = client.post("/qrz-token", json={"callsign": "AB1CD", "token": ""})
        assert response.status_code == 400

    def test_save_token_without_any_creds_returns_400(self):
        response = client.post("/qrz-token", json={})
        assert response.status_code == 400

    def test_save_valid_token_succeeds(self, tmp_path, monkeypatch):
        from src.qrz_config import _CONFIG_FILE

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

        mock_session = self._make_mock_session('RESULT=OK&BOOKID=12345&CALLSIGN=AB1CD')

        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = client.post("/qrz-token", json={"callsign": "AB1CD", "token": "validtoken"})

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert data['validated'] is True

    def test_save_invalid_token_returns_422(self, tmp_path, monkeypatch):
        from src.qrz_config import _CONFIG_FILE

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

        mock_session = self._make_mock_session('RESULT=FAIL&REASON=Invalid+key')

        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = client.post("/qrz-token", json={"callsign": "AB1CD", "token": "badtoken"})

        assert response.status_code == 422
        data = response.json()
        assert 'validation failed' in data['detail'].lower() or 'invalid' in data['detail'].lower()

    def test_save_invalid_token_does_not_save(self, tmp_path, monkeypatch):
        from src.qrz_config import _CONFIG_FILE, save_qrz_data

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

        # Pre-create config with existing data
        temp_config.write_text('{"existing_field": "value"}')

        mock_session = self._make_mock_session('RESULT=FAIL&REASON=Expired+key')

        with patch('aiohttp.ClientSession', return_value=mock_session):
            client.post("/qrz-token", json={"callsign": "AB1CD", "token": "expiredtoken"})

        # Config should be unchanged - callsign not updated
        import json
        config_data = json.loads(temp_config.read_text())
        assert config_data.get('callsign') != 'AB1CD'
        assert config_data.get('existing_field') == 'value'

    def test_save_token_with_session_token_return(self, tmp_path, monkeypatch):
        from src.qrz_config import _CONFIG_FILE

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

        auth_response = 'RESULT=OK&BOOKID=12345&CALLSIGN=AB1CD&SESSIONTOKEN=newsessiontoken'
        mock_session = self._make_mock_session(auth_response)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = client.post("/qrz-token", json={"callsign": "AB1CD", "token": "oldtoken"})

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert data['validated'] is True

    def test_save_token_http_error_returns_422(self, tmp_path, monkeypatch):
        from src.qrz_config import _CONFIG_FILE

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

        mock_resp = AsyncMock()
        mock_resp.status = 401
        mock_resp.read = AsyncMock(return_value=b'Unauthorized')
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = client.post("/qrz-token", json={"callsign": "AB1CD", "token": "badtoken"})

        assert response.status_code == 422


class TestSyncNeedsRenewal:
    """Tests that sync_qso_data returns needs_renewal on auth failure."""

    @pytest.fixture
    def mock_cache(self, tmp_path, monkeypatch):
        from src.qrz_qso import QSO_CACHE_FILE
        cache_file = tmp_path / "dxscraper_qso.jsonl"
        monkeypatch.setattr('src.qrz_qso.QSO_CACHE_FILE', cache_file)
        return cache_file

    @pytest.mark.asyncio
    async def test_auth_failure_includes_needs_renewal(self, mock_cache):
        from src.qrz_qso import sync_qso_data

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=b'RESULT=FAIL&REASON=Invalid+key')
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await sync_qso_data('AB1CD', 'badtoken')

        assert result['status'] == 'error'
        assert result['needs_renewal'] is True
        assert 'FAIL' in result['error']

    @pytest.mark.asyncio
    async def test_auth_http_error_includes_needs_renewal(self, mock_cache):
        from src.qrz_qso import sync_qso_data

        mock_resp = AsyncMock()
        mock_resp.status = 401
        mock_resp.read = AsyncMock(return_value=b'Unauthorized')
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await sync_qso_data('AB1CD', 'expiredtoken')

        assert result['status'] == 'error'
        assert result['needs_renewal'] is True

    @pytest.mark.asyncio
    async def test_successful_sync_has_no_needs_renewal(self, mock_cache):
        from src.qrz_qso import sync_qso_data, QSO_CACHE_FILE

        auth_ok = 'RESULT=OK&BOOKID=12345&CALLSIGN=AB1CD'
        fetch_ok = 'RESULT=OK&COUNT=0&ADIF='

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(side_effect=[auth_ok.encode(), fetch_ok.encode()])
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await sync_qso_data('AB1CD', 'validtoken')

        assert result['status'] == 'ok'
        assert result.get('needs_renewal') is None

    @pytest.mark.asyncio
    async def test_network_error_includes_needs_renewal(self, mock_cache):
        from src.qrz_qso import sync_qso_data

        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=Exception('Connection refused'))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await sync_qso_data('AB1CD', 'testtoken')

        assert result['status'] == 'error'
        assert result['needs_renewal'] is True


class TestQRZSyncReturnsNeedsRenewal:
    """Tests that /qrz-sync returns needs_renewal when token is bad."""

    def test_qrz_sync_with_expired_token_returns_502_with_needs_renewal(self, tmp_path, monkeypatch, mocker):
        from src.qrz_config import save_qrz_data, _CONFIG_FILE

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

        save_qrz_data('AB1CD', 'expiredtoken')

        mock_sync = AsyncMock(return_value={'status': 'error', 'error': 'Auth failed: RESULT=FAIL (REASON=Expired key)', 'needs_renewal': True})
        mocker.patch('src.api.sync_qso_data', mock_sync)

        response = client.get("/qrz-sync")
        assert response.status_code == 502
        data = response.json()
        assert data['status'] == 'error'
        assert data['needs_renewal'] is True


class TestDebugQRZRenewal:
    """Tests for CLI --debug-qrz token renewal flow."""

    @pytest.mark.asyncio
    async def test_debug_qrz_renewal_on_auth_failure(self, tmp_path, monkeypatch, mocker):
        from src.main import _debug_qrz
        from src.qrz_config import _CONFIG_FILE, _KEYRING_SERVICE, _KEYRING_USER
        from src.qrz_qso import QSO_CACHE_FILE

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)
        temp_cache = tmp_path / "dxscraper_qso.jsonl"
        monkeypatch.setattr('src.qrz_qso.QSO_CACHE_FILE', temp_cache)

        # Pre-save credentials so _debug_qrz finds them
        save_qrz_data = __import__('src.qrz_config', fromlist=['save_qrz_data']).save_qrz_data
        save_qrz_data('AB1CD', 'expiredtoken')

        # Mock keyring to return the saved token
        mock_keyring = MagicMock()
        mock_keyring.get_password = MagicMock(return_value='expiredtoken')

        # First sync fails (expired), then succeeds with new token
        call_count = [0]
        async def mock_sync(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {'status': 'error', 'error': 'Auth failed: RESULT=FAIL (REASON=Expired key)', 'needs_renewal': True}
            return {'status': 'ok', 'total_qsos': 50, 'synced_count': 50}

        mock_sync_fn = MagicMock(side_effect=mock_sync)

        # Patch where the names are used in src.main module
        with patch('src.main.sync_qso_data', mock_sync_fn):
            with patch('src.main._authenticate', AsyncMock(return_value='newtoken')):
                with patch('src.main.save_qrz_data') as save_qrz_data_mock:
                    with patch('builtins.input', return_value='newtoken123'):
                        with patch('keyring.get_password', mock_keyring.get_password):
                            import sys
                            from io import StringIO
                            captured = StringIO()
                            with patch('sys.stdout', captured):
                                with patch.object(sys, 'exit'):
                                    await _debug_qrz()

        # Should have called sync twice (initial + after renewal)
        assert mock_sync_fn.call_count == 2

        # Should have saved the new token
        assert save_qrz_data_mock.called
        save_args = save_qrz_data_mock.call_args
        assert save_args[0][0] == 'AB1CD'
        assert save_args[0][1] == 'newtoken123'

        # Should have detected expired token
        assert 'expired' in captured.getvalue().lower()

    @pytest.mark.asyncio
    async def test_debug_qrz_renewal_user_quits(self, tmp_path, monkeypatch, mocker):
        from src.main import _debug_qrz
        from src.qrz_config import _CONFIG_FILE

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

        save_qrz_data = __import__('src.qrz_config', fromlist=['save_qrz_data']).save_qrz_data
        save_qrz_data('AB1CD', 'expiredtoken')

        mock_sync = AsyncMock(return_value={'status': 'error', 'error': 'Auth failed', 'needs_renewal': True})

        with patch('src.main.sync_qso_data', mock_sync):
            with patch('builtins.input', return_value='q'):
                with patch('keyring.get_password', MagicMock(return_value='expiredtoken')):
                    import sys
                    from io import StringIO
                    captured = StringIO()
                    with patch('sys.stdout', captured):
                        with patch.object(sys, 'exit') as mock_exit:
                            await _debug_qrz()

        # Should have exited with code 0 (user chose to quit)
        calls_with_zero = [c for c in mock_exit.call_args_list if c[0][0] == 0]
        assert len(calls_with_zero) >= 1

    @pytest.mark.asyncio
    async def test_debug_qrz_renewal_empty_token_retries(self, tmp_path, monkeypatch, mocker):
        from src.main import _debug_qrz
        from src.qrz_config import _CONFIG_FILE

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

        save_qrz_data = __import__('src.qrz_config', fromlist=['save_qrz_data']).save_qrz_data
        save_qrz_data('AB1CD', 'expiredtoken')

        call_count = [0]
        async def mock_sync(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {'status': 'error', 'error': 'Auth failed', 'needs_renewal': True}
            return {'status': 'ok', 'total_qsos': 50, 'synced_count': 50}

        mock_sync_fn = MagicMock(side_effect=mock_sync)

        with patch('src.main.sync_qso_data', mock_sync_fn):
            with patch('src.main._authenticate', AsyncMock(return_value='newtoken')):
                with patch('src.main.save_qrz_data') as save_qrz_data_mock:
                    with patch('builtins.input', side_effect=['', 'newtoken123']):
                        with patch('keyring.get_password', MagicMock(return_value='expiredtoken')):
                            import sys
                            from io import StringIO
                            captured = StringIO()
                            with patch('sys.stdout', captured):
                                with patch.object(sys, 'exit'):
                                    await _debug_qrz()

        # Should have called sync twice
        assert mock_sync_fn.call_count == 2
        assert save_qrz_data_mock.called

    @pytest.mark.asyncio
    async def test_debug_qrz_renewal_max_attempts_exceeded(self, tmp_path, monkeypatch, mocker):
        from src.main import _debug_qrz
        from src.qrz_config import _CONFIG_FILE

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

        save_qrz_data = __import__('src.qrz_config', fromlist=['save_qrz_data']).save_qrz_data
        save_qrz_data('AB1CD', 'expiredtoken')

        mock_sync = AsyncMock(return_value={'status': 'error', 'error': 'Auth failed', 'needs_renewal': True})

        with patch('src.main.sync_qso_data', mock_sync):
            with patch('src.main._authenticate', side_effect=QRZDataError('Invalid key')):
                with patch('builtins.input', side_effect=['bad1', 'bad2', 'bad3', 'q']):
                    with patch('keyring.get_password', MagicMock(return_value='expiredtoken')):
                        import sys
                        from io import StringIO
                        captured = StringIO()
                        with patch('sys.stdout', captured):
                            with patch.object(sys, 'exit') as mock_exit:
                                await _debug_qrz()

        # Should have exited with code 1
        calls_with_one = [c for c in mock_exit.call_args_list if c[0][0] == 1]
        assert len(calls_with_one) >= 1
        assert 'Max attempts reached' in captured.getvalue()

    @pytest.mark.asyncio
    async def test_debug_qrz_no_renewal_needed_on_success(self, tmp_path, monkeypatch, mocker):
        from src.main import _debug_qrz
        from src.qrz_config import _CONFIG_FILE

        temp_config = tmp_path / "dxscraper_config.json"
        monkeypatch.setattr('src.qrz_config._CONFIG_FILE', temp_config)

        save_qrz_data = __import__('src.qrz_config', fromlist=['save_qrz_data']).save_qrz_data
        save_qrz_data('AB1CD', 'validtoken')

        mock_sync = AsyncMock(return_value={'status': 'ok', 'total_qsos': 100, 'synced_count': 100})

        with patch('src.main.sync_qso_data', mock_sync):
            with patch('keyring.get_password', MagicMock(return_value='validtoken')):
                import sys
                from io import StringIO
                captured = StringIO()
                with patch('sys.stdout', captured):
                    with patch.object(sys, 'exit'):
                        await _debug_qrz()

        # Should not have prompted for renewal
        assert 'expired' not in captured.getvalue().lower()
        assert mock_sync.call_count == 1
