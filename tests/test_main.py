import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from src.main import main, parse_args, run_with_filter, main_entry, resolve_source_name
from src.models import DXStation, DXDataSummary
from src.service import DXPeditionService
from src.config import Config


class TestParseArgs:
    """Tests for parse_args function"""

    def test_parse_args_default_values(self):
        """Test parse_args with default values"""
        with patch('sys.argv', ['script_name']):
            args = parse_args()
            assert args.max_age == 3600
            assert args.format == "json"
            assert args.source is None

    def test_parse_args_custom_max_age(self):
        """Test parse_args with custom max_age"""
        with patch('sys.argv', ['script_name', '--max-age', '7200']):
            args = parse_args()
            assert args.max_age == 7200

    def test_parse_args_custom_format(self):
        """Test parse_args with custom format"""
        with patch('sys.argv', ['script_name', '--format', 'table']):
            args = parse_args()
            assert args.format == "table"

    def test_parse_args_custom_source(self):
        """Test parse_args with custom source"""
        with patch('sys.argv', ['script_name', '--source', 'dx_summit']):
            args = parse_args()
            assert args.source == "dx_summit"

    def test_parse_args_debug_qrz(self):
        with patch('sys.argv', ['script_name', '--debug-qrz']):
            args = parse_args()
            assert args.debug_qrz is True

    def test_parse_args_invalid_source_rejected(self):
        with patch('sys.argv', ['script_name', '--source', 'not-a-source']):
            with pytest.raises(SystemExit):
                parse_args()

    def test_parse_args_accepts_all_configured_sources(self):
        for key in ("dx_summit", "dx_cluster", "dx_news", "hamqth", "pota", "ng3k", "dxcluster"):
            with patch('sys.argv', ['script_name', '--source', key]):
                args = parse_args()
                assert args.source == key


class TestMain:
    """Tests for main async function"""

    @pytest.mark.asyncio
    async def test_main_json_output(self, capsys):
        """Test main function with JSON output format"""
        mock_summary = DXDataSummary(
            total_stations=5,
            active_stations=3,
            last_refresh=datetime.now(timezone.utc),
            data_sources=["dx_summit"],
            stations=[]
        )
        
        with patch.object(DXPeditionService, '__init__', return_value=None):
            with patch.object(DXPeditionService, 'get_current_data', new_callable=AsyncMock, return_value=mock_summary):
                result = await main(max_age_seconds=3600, output_format="json")
                
                captured = capsys.readouterr()
                assert '"total_stations": 5' in captured.out
                assert '"active_stations": 3' in captured.out
                assert result == mock_summary

    @pytest.mark.asyncio
    async def test_main_table_output(self, capsys):
        """Test main function with table output format"""
        station = DXStation(
            callsign="TEST123",
            dx_country="Test Country",
            spotter="Test Spotter",
            band="20m",
            mode="SSB",
            comment="Test Comment",
            last_update=datetime.now(timezone.utc),
            source="test_source",
            status="active"
        )
        
        mock_summary = DXDataSummary(
            total_stations=1,
            active_stations=1,
            last_refresh=datetime.now(timezone.utc),
            data_sources=["test_source"],
            stations=[station]
        )
        
        with patch.object(DXPeditionService, '__init__', return_value=None):
            with patch.object(DXPeditionService, 'get_current_data', new_callable=AsyncMock, return_value=mock_summary):
                result = await main(max_age_seconds=3600, output_format="table")
                
                captured = capsys.readouterr()
                assert "TEST123" in captured.out
                assert "Test Country" in captured.out
                assert result == mock_summary

    @pytest.mark.asyncio
    async def test_main_unknown_format(self, capsys):
        """Test main function with unknown output format"""
        mock_summary = DXDataSummary(
            total_stations=0,
            active_stations=0,
            last_refresh=datetime.now(timezone.utc),
            data_sources=[],
            stations=[]
        )
        
        with patch.object(DXPeditionService, '__init__', return_value=None):
            with patch.object(DXPeditionService, 'get_current_data', new_callable=AsyncMock, return_value=mock_summary):
                result = await main(max_age_seconds=3600, output_format="unknown")
                
                captured = capsys.readouterr()
                assert "Unknown format: unknown" in captured.out
                assert result == mock_summary

    @pytest.mark.asyncio
    async def test_main_with_max_age_override(self, capsys):
        """Test main function with max_age override"""
        mock_summary = DXDataSummary(
            total_stations=2,
            active_stations=2,
            last_refresh=datetime.now(timezone.utc),
            data_sources=["test"],
            stations=[]
        )
        
        with patch.object(DXPeditionService, '__init__', return_value=None):
            with patch.object(DXPeditionService, 'get_current_data', new_callable=AsyncMock, return_value=mock_summary):
                result = await main(max_age_seconds=1800, output_format="json")
                
                captured = capsys.readouterr()
                assert '"total_stations": 2' in captured.out
                assert result == mock_summary

    @pytest.mark.asyncio
    async def test_main_filters_by_live_source_name(self, capsys):
        """CLI --source dx_summit matches station.source 'DX Summit'."""
        now = datetime.now(timezone.utc)
        summit = DXStation(
            callsign="W1AW",
            dx_country="United States",
            spotter="K1AR",
            band="20m",
            last_update=now,
            source="DX Summit",
            status="active",
        )
        pota = DXStation(
            callsign="N1ABC",
            dx_country="US-CT",
            spotter="N1ABC",
            band="40m",
            last_update=now,
            source="POTA",
            status="active",
        )
        mock_summary = DXDataSummary(
            total_stations=2,
            active_stations=2,
            last_refresh=now,
            data_sources=["DX Summit", "POTA"],
            stations=[summit, pota],
        )
        with patch.object(DXPeditionService, '__init__', return_value=None):
            with patch.object(DXPeditionService, 'get_current_data', new_callable=AsyncMock, return_value=mock_summary):
                result = await main(max_age_seconds=3600, output_format="json", source="dx_summit")
        assert result.total_stations == 1
        assert result.stations[0].callsign == "W1AW"
        assert result.data_sources == ["DX Summit"]

    @pytest.mark.asyncio
    async def test_main_table_output_with_sources_and_no_frequency(self, capsys):
        station = DXStation(
            callsign="TEST1",
            dx_country="Palau",
            spotter="Spotter",
            band="20m",
            frequency=None,
            mode="",
            comment="via sources",
            last_update=datetime.now(timezone.utc),
            source="DX Summit",
            sources=["DX Summit", "POTA"],
            status="active",
        )
        mock_summary = DXDataSummary(
            total_stations=1,
            active_stations=1,
            last_refresh=datetime.now(timezone.utc),
            data_sources=["DX Summit"],
            stations=[station],
        )
        with patch.object(DXPeditionService, '__init__', return_value=None):
            with patch.object(DXPeditionService, 'get_current_data', new_callable=AsyncMock, return_value=mock_summary):
                await main(max_age_seconds=3600, output_format="table")
        captured = capsys.readouterr()
        assert "TEST1" in captured.out
        assert "DX Summit, POTA" in captured.out

    @pytest.mark.asyncio
    async def test_main_reraises_exceptions(self):
        with patch.object(DXPeditionService, '__init__', return_value=None):
            with patch.object(DXPeditionService, 'get_current_data', new_callable=AsyncMock, side_effect=RuntimeError("boom")):
                with pytest.raises(RuntimeError, match="boom"):
                    await main(max_age_seconds=3600, output_format="json")


class TestRunWithFilter:
    """Tests for run_with_filter function"""

    @pytest.mark.asyncio
    async def test_run_with_filter_no_source(self):
        """Test run_with_filter without source filter"""
        station1 = DXStation(
            callsign="TEST1",
            dx_country="Loc 1",
            spotter="Spotter 1",
            band="20m",
            last_update=datetime.now(timezone.utc),
            source="source1",
            status="active"
        )
        station2 = DXStation(
            callsign="TEST2",
            dx_country="Loc 2",
            spotter="Spotter 2",
            band="40m",
            last_update=datetime.now(timezone.utc),
            source="source2",
            status="active"
        )
        
        mock_summary = DXDataSummary(
            total_stations=2,
            active_stations=2,
            last_refresh=datetime.now(timezone.utc),
            data_sources=["source1", "source2"],
            stations=[station1, station2]
        )
        
        args = MagicMock()
        args.max_age = 3600
        args.source = None
        
        with patch.object(DXPeditionService, "get_current_data", new_callable=AsyncMock, return_value=mock_summary):
            result = await run_with_filter(args)
        
        assert result.total_stations == 2
        assert len(result.stations) == 2

    @pytest.mark.asyncio
    async def test_run_with_filter_source(self):
        """Test run_with_filter with source filter"""
        station1 = DXStation(
            callsign="TEST1",
            dx_country="Loc 1",
            spotter="Spotter 1",
            band="20m",
            last_update=datetime.now(timezone.utc),
            source="DX Summit",
            status="active"
        )
        station2 = DXStation(
            callsign="TEST2",
            dx_country="Loc 2",
            spotter="Spotter 2",
            band="40m",
            last_update=datetime.now(timezone.utc),
            source="Spothole",
            status="active"
        )
        
        mock_summary = DXDataSummary(
            total_stations=2,
            active_stations=2,
            last_refresh=datetime.now(timezone.utc),
            data_sources=["DX Summit", "Spothole"],
            stations=[station1, station2]
        )
        
        args = MagicMock()
        args.max_age = 3600
        args.source = "dx_summit"
        
        with patch.object(DXPeditionService, '__init__', return_value=None):
            with patch.object(DXPeditionService, 'get_current_data', new_callable=AsyncMock, return_value=mock_summary):
                result = await run_with_filter(args)
                
                assert result.total_stations == 1
                assert len(result.stations) == 1
                assert result.stations[0].callsign == "TEST1"


class TestMainEntry:
    """Tests for main_entry function"""

    @pytest.mark.asyncio
    async def test_main_entry(self, capsys):
        """Test main_entry function"""
        mock_summary = DXDataSummary(
            total_stations=1,
            active_stations=1,
            last_refresh=datetime.now(timezone.utc),
            data_sources=["test"],
            stations=[]
        )
        
        with patch('sys.argv', ['script_name', '--max-age', '1800', '--format', 'json']):
            with patch.object(DXPeditionService, '__init__', return_value=None):
                with patch.object(DXPeditionService, 'get_current_data', new_callable=AsyncMock, return_value=mock_summary):
                    with patch('src.main.main', new_callable=AsyncMock) as mock_main:
                        await main_entry()
                        mock_main.assert_called_once_with(1800, 'json', source=None)

    @pytest.mark.asyncio
    async def test_main_entry_debug_qrz_skips_main(self):
        with patch('sys.argv', ['script_name', '--debug-qrz']):
            with patch('src.main._debug_qrz', new_callable=AsyncMock) as mock_debug:
                with patch('src.main.main', new_callable=AsyncMock) as mock_main:
                    await main_entry()
                    mock_debug.assert_called_once()
                    mock_main.assert_not_called()


class TestResolveSourceName:
    def test_config_keys_map_to_display_names(self):
        assert resolve_source_name("dx_summit") == "DX Summit"
        assert resolve_source_name("dx_cluster") == "Spothole"
        assert resolve_source_name("dx_news") == "DX News"
        assert resolve_source_name("hamqth") == "HamQTH"
        assert resolve_source_name("pota") == "POTA"
        assert resolve_source_name("ng3k") == "NG3K"

    def test_dxcluster_alias(self):
        assert resolve_source_name("dxcluster") == "Spothole"

    def test_none_and_unknown_passthrough(self):
        assert resolve_source_name(None) is None
        assert resolve_source_name("DX Summit") == "DX Summit"


