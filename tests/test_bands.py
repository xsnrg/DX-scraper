import pytest
from src.bands import frequency_to_band, band_to_range, BAND_RANGES


class TestBandRanges:
    def test_all_bands_have_ranges(self):
        expected = {"160m", "80m", "40m", "30m", "20m", "17m", "15m", "12m", "10m", "6m", "2m", "70cm"}
        assert set(BAND_RANGES.keys()) == expected

    def test_160m_range(self):
        assert band_to_range("160m") == (1.800, 2.000)

    def test_80m_range(self):
        assert band_to_range("80m") == (3.500, 4.000)

    def test_40m_range(self):
        assert band_to_range("40m") == (7.000, 7.300)

    def test_20m_range(self):
        assert band_to_range("20m") == (14.000, 14.350)

    def test_70cm_range(self):
        assert band_to_range("70cm") == (420.000, 450.000)

    def test_unknown_band_returns_none(self):
        assert band_to_range("999m") is None


class TestFrequencyToBand:
    def test_14_074_is_20m(self):
        assert frequency_to_band(14.074) == "20m"

    def test_14_000_is_20m(self):
        assert frequency_to_band(14.000) == "20m"

    def test_14_350_is_20m(self):
        assert frequency_to_band(14.350) == "20m"

    def test_14_351_is_not_20m(self):
        assert frequency_to_band(14.351) is None

    def test_7_074_is_40m(self):
        assert frequency_to_band(7.074) == "40m"

    def test_3_700_is_80m(self):
        assert frequency_to_band(3.700) == "80m"

    def test_28_500_is_10m(self):
        assert frequency_to_band(28.500) == "10m"

    def test_21_060_is_15m(self):
        assert frequency_to_band(21.060) == "15m"

    def test_18_100_is_17m(self):
        assert frequency_to_band(18.100) == "17m"

    def test_24_900_is_12m(self):
        assert frequency_to_band(24.900) == "12m"

    def test_10_125_is_30m(self):
        assert frequency_to_band(10.125) == "30m"

    def test_50_100_is_6m(self):
        assert frequency_to_band(50.100) == "6m"

    def test_145_000_is_2m(self):
        assert frequency_to_band(145.000) == "2m"

    def test_432_000_is_70cm(self):
        assert frequency_to_band(432.000) == "70cm"

    def test_1_900_is_160m(self):
        assert frequency_to_band(1.900) == "160m"

    def test_below_all_bands(self):
        assert frequency_to_band(1.000) is None

    def test_above_all_bands(self):
        assert frequency_to_band(500.000) is None

    def test_between_80m_and_40m(self):
        assert frequency_to_band(5.000) is None

    def test_between_40m_and_30m(self):
        assert frequency_to_band(8.000) is None

    def test_between_30m_and_20m(self):
        assert frequency_to_band(12.000) is None

    def test_between_20m_and_17m(self):
        assert frequency_to_band(15.000) is None

    def test_between_17m_and_15m(self):
        assert frequency_to_band(19.000) is None

    def test_between_15m_and_12m(self):
        assert frequency_to_band(22.000) is None

    def test_between_12m_and_10m(self):
        assert frequency_to_band(26.000) is None

    def test_between_10m_and_6m(self):
        assert frequency_to_band(40.000) is None

    def test_between_6m_and_2m(self):
        assert frequency_to_band(100.000) is None

    def test_between_2m_and_70cm(self):
        assert frequency_to_band(250.000) is None
