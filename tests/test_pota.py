from playwright.sync_api import Page, expect
import re

from conftest import _mock_data, open_dashboard


def test_pota_toggle_button_visible(page: Page):
    """POTA toggle button is visible on the dashboard."""
    open_dashboard(page)
    expect(page.get_by_role("button", name="POTA enabled")).to_be_visible()


def test_pota_toggle_default_state(page: Page):
    """POTA toggle defaults to enabled (purple) state."""
    open_dashboard(page)
    pota_btn = page.get_by_role("button", name="POTA enabled")
    expect(pota_btn).to_have_class(re.compile(r"bg-purple-600"))


def test_pota_toggle_text(page: Page):
    """POTA toggle shows correct text when enabled."""
    open_dashboard(page)
    expect(page.get_by_text("POTA enabled")).to_be_visible()


def test_pota_toggle_refetches_without_pota(page: Page):
    """Turning POTA off re-fetches /data?exclude_sources=POTA and hides POTA rows."""
    with_pota = _mock_data(num_stations=5)
    without_pota = dict(with_pota)
    without_pota["stations"] = [s for s in with_pota["stations"] if s["source"] != "POTA"]
    without_pota["total_stations"] = len(without_pota["stations"])
    without_pota["active_stations"] = without_pota["total_stations"]
    seen = []

    def data_for(route):
        seen.append(route.request.url)
        if "exclude_sources=POTA" in route.request.url:
            return without_pota
        return with_pota

    open_dashboard(page, data=data_for)
    expect(page.get_by_role("cell", name="P29V")).to_be_visible()

    page.get_by_role("button", name="POTA enabled").click()
    expect(page.get_by_role("button", name="Activate POTA")).to_be_visible()
    expect(page.get_by_role("cell", name="P29V")).not_to_be_visible()
    expect(page.get_by_role("cell", name="W1AW")).to_be_visible()
    assert any("exclude_sources=POTA" in url for url in seen)


def test_pota_rows_display_band_from_api(page: Page):
    """POTA rows display the band provided by the API (filled from frequency)."""
    mock = _mock_data(num_stations=3)
    for s in mock["stations"]:
        if s["source"] == "POTA":
            s["band"] = "20m"
            s["frequency"] = 14.270
    open_dashboard(page, mock)
    pota_row = page.locator("tr").filter(has_text="P29V")
    expect(pota_row.get_by_text("20m")).to_be_visible()


def test_frequencies_displayed_in_mhz_range(page: Page):
    """Frequencies are displayed in MHz (1-999 range), not kHz."""
    open_dashboard(page, _mock_data(num_stations=5))
    freq_cells = page.locator("td.text-sm.font-mono").all()
    mhz_values = []
    for cell in freq_cells:
        text = cell.inner_text()
        if text and "MHz" in text:
            num = float(text.replace("MHz", "").strip())
            assert 1 <= num <= 999, f"Frequency {num} MHz is out of valid MHz range: {text}"
            mhz_values.append(num)
    assert mhz_values, "Expected at least one frequency cell with an MHz suffix"


def test_frequencies_displayed_with_mhz_suffix(page: Page):
    """All frequency cells show MHz suffix."""
    open_dashboard(page, _mock_data(num_stations=5))
    freq_cells = page.locator("td.text-sm.font-mono").all()
    assert freq_cells, "Expected frequency cells"
    for cell in freq_cells:
        text = cell.inner_text()
        if text and text != "N/A":
            assert "MHz" in text, f"Frequency cell should show MHz suffix: {text}"
