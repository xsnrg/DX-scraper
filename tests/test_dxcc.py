"""Unit tests for DXCC country lookup and ADIF resolution."""
import pytest

from src.dxcc import DXCC_LOOKUP, get_dxcc_number, resolve_dxcc


class TestGetDxccNumber:
    def test_known_entities(self):
        assert get_dxcc_number("United States") == "291"
        assert get_dxcc_number("Hawaii") == "110"
        assert get_dxcc_number("Japan") == "339"
        assert get_dxcc_number("Canada") == "1"
        assert get_dxcc_number("Australia") == "150"
        assert get_dxcc_number("Fed. Rep. of Germany") == "230"

    def test_empty_string_returns_none(self):
        assert get_dxcc_number("") is None

    def test_unknown_name_returns_none(self):
        assert get_dxcc_number("USA") is None
        assert get_dxcc_number("Germany") is None
        assert get_dxcc_number("Not A Country") is None

    def test_lookup_is_case_sensitive(self):
        assert get_dxcc_number("united states") is None
        assert get_dxcc_number("UNITED STATES") is None

    def test_lookup_has_expected_size(self):
        assert len(DXCC_LOOKUP) >= 300
        assert "United States" in DXCC_LOOKUP
        assert "Hawaii" in DXCC_LOOKUP


class TestResolveDxcc:
    def test_prefers_adif_over_country(self):
        assert resolve_dxcc("Japan", adif="291") == "291"

    def test_strips_leading_zeros_from_adif(self):
        assert resolve_dxcc("Japan", adif="0339") == "339"
        assert resolve_dxcc("United States", adif="0291") == "291"

    def test_all_zeros_adif_becomes_empty(self):
        assert resolve_dxcc("Japan", adif="000") == ""
        assert resolve_dxcc("Japan", adif="0") == ""

    def test_whitespace_adif_falls_back_to_country(self):
        assert resolve_dxcc("Japan", adif="   ") == "339"
        assert resolve_dxcc("Japan", adif="") == "339"

    def test_adif_none_falls_back_to_country(self):
        assert resolve_dxcc("Japan") == "339"
        assert resolve_dxcc("Japan", adif=None) == "339"

    def test_strips_surrounding_whitespace_on_adif(self):
        assert resolve_dxcc("Japan", adif="  291  ") == "291"

    def test_unknown_country_without_adif_returns_empty(self):
        assert resolve_dxcc("USA") == ""
        assert resolve_dxcc("Not A Country") == ""

    def test_missing_both_returns_empty(self):
        assert resolve_dxcc("") == ""
        assert resolve_dxcc("", adif=None) == ""
        assert resolve_dxcc("", adif="") == ""

    def test_adif_used_even_when_country_empty(self):
        assert resolve_dxcc("", adif="110") == "110"
