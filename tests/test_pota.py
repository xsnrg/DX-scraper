import json
import re
import pytest
from playwright.sync_api import Page, expect
from conftest import _mock_data


def test_pota_toggle_button_visible(page: Page):
    """POTA toggle button is visible on the dashboard."""
    page.goto("http://localhost:8000")
    expect(page.get_by_role("button", name="POTA")).to_be_visible()


def test_pota_toggle_default_state(page: Page):
    """POTA toggle defaults to enabled (purple) state."""
    page.goto("http://localhost:8000")
    pota_btn = page.get_by_role("button", name="POTA")
    expect(pota_btn).to_have_class(re.compile(r'bg-purple-600'))


def test_pota_toggle_text(page: Page):
    """POTA toggle shows correct text when enabled."""
    page.goto("http://localhost:8000")
    expect(page.get_by_text("POTA enabled")).to_be_visible()


def test_pota_rows_display_band_via_frequency(page: Page):
    """POTA rows with empty band display band derived from frequency."""
    mock = _mock_data(num_stations=3)
    # POTA station with empty band but valid frequency
    for s in mock["stations"]:
        if s["source"] == "POTA":
            s["band"] = ""
            s["frequency"] = 7047.0  # kHz value that should convert to 40m
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.goto("http://localhost:8000")
    
    # Should show "40m" derived from frequency (7.047 MHz)
    expect(page.get_by_text("40m")).to_be_visible()


def test_frequencies_displayed_in_mhz_range(page: Page):
    """Frequencies are displayed in MHz (1-999 range), not kHz."""
    mock = _mock_data(num_stations=5)
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.goto("http://localhost:8000")
    
    # Check that frequencies are in MHz format (e.g., "7.0740 MHz") not kHz (e.g., "7074.0000 MHz")
    freq_cells = page.locator("td.text-sm.font-mono").all()
    for cell in freq_cells:
        text = cell.inner_text()
        if text and "MHz" in text:
            # Extract numeric part
            num_str = text.replace("MHz", "").strip()
            num = float(num_str)
            assert 1 <= num <= 999, f"Frequency {num} MHz is out of valid MHz range (1-999). Was {text}"


def test_frequencies_displayed_with_mhz_suffix(page: Page):
    """All frequency cells show MHz suffix."""
    mock = _mock_data(num_stations=5)
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.goto("http://localhost:8000")
    
    freq_cells = page.locator("td.text-sm.font-mono").all()
    for cell in freq_cells:
        text = cell.inner_text()
        if text and text != "N/A":
            assert "MHz" in text, f"Frequency cell should show MHz suffix: {text}"
