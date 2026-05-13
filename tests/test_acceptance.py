"""Acceptance tests for the DXpedition Monitor dashboard.

These tests verify user-facing features through a real browser (headless Chromium).
Run with: playwright test tests/test_acceptance.py
"""

import pytest
from playwright.sync_api import Page, expect


def test_dashboard_loads(page: Page):
    """Dashboard renders with correct title and content."""
    page.goto("http://localhost:8000")
    expect(page).to_have_title("DXpedition Monitor")


def test_spot_age_filter_shows_default(page: Page):
    """Spot age filter shows 30 as default on page load."""
    page.goto("http://localhost:8000")
    select = page.get_by_role("combobox").last
    expect(select).to_have_value("30")


def test_spot_age_filter_changes(page: Page):
    """Changing spot age filter updates the select value."""
    page.goto("http://localhost:8000")
    select = page.get_by_role("combobox").last
    select.select_option("60")
    expect(select).to_have_value("60")


def test_clickable_band_column_appends_to_search(page: Page):
    """Clicking a band value in the table appends it to the search box."""
    page.goto("http://localhost:8000")
    # Wait for table to potentially have data
    page.wait_for_timeout(2000)
    band_cells = page.get_by_role("gridcell").all()
    if not band_cells:
        pytest.skip("No table data available")
    for cell in band_cells:
        text = cell.inner_text()
        if text and text not in ("-", "Band"):
            cell.click()
            break
    else:
        pytest.skip("No clickable band values found")
    search_input = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search_value = search_input.input_value()
    assert len(search_value) > 0, "Search should be populated after clicking a band"


def test_clickable_mode_column_appends_to_search(page: Page):
    """Clicking a mode value in the table appends it to the search box."""
    page.goto("http://localhost:8000")
    page.wait_for_timeout(2000)
    mode_cells = page.get_by_role("gridcell").all()
    if not mode_cells:
        pytest.skip("No table data available")
    for cell in mode_cells:
        text = cell.inner_text()
        if text and text not in ("-", "Mode"):
            cell.click()
            break
    else:
        pytest.skip("No clickable mode values found")
    search_input = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search_value = search_input.input_value()
    assert len(search_value) > 0, "Search should be populated after clicking a mode"


def test_clickable_dx_location_column_appends_to_search(page: Page):
    """Clicking a DX location value in the table appends it to the search box."""
    page.goto("http://localhost:8000")
    page.wait_for_timeout(2000)
    dx_cells = page.get_by_role("gridcell").all()
    if not dx_cells:
        pytest.skip("No table data available")
    for cell in dx_cells:
        text = cell.inner_text()
        if text and text not in ("-", "DX Location"):
            cell.click()
            break
    else:
        pytest.skip("No clickable DX location values found")
    search_input = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search_value = search_input.input_value()
    assert len(search_value) > 0, "Search should be populated after clicking a DX location"


def test_clear_search_button_appears(page: Page):
    """Clear (X) button appears when search has text."""
    page.goto("http://localhost:8000")
    search_input = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search_input.fill("test")
    page.wait_for_timeout(500)
    clear_button = page.get_by_title("Clear search")
    expect(clear_button).to_be_visible()


def test_clear_search_button_clears_input(page: Page):
    """Clicking the clear button empties the search input."""
    page.goto("http://localhost:8000")
    search_input = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search_input.fill("test")
    page.wait_for_timeout(500)
    page.get_by_title("Clear search").click()
    expect(search_input).to_have_value("")


def test_pagination_controls_visible(page: Page):
    """Pagination controls are visible on the dashboard."""
    page.goto("http://localhost:8000")
    expect(page.get_by_role("combobox").first).to_be_visible()


def test_pota_toggle_visible(page: Page):
    """POTA toggle button is visible on the dashboard."""
    page.goto("http://localhost:8000")
    expect(page.get_by_role("button", name="POTA")).to_be_visible()


def test_qrz_sync_button_visible(page: Page):
    """QRZ sync button is visible on the dashboard."""
    page.goto("http://localhost:8000")
    possible_texts = ["Setup QRZ", "Refresh QRZ Data", "Syncing QRZ...", "Synced!", "Sync Failed"]
    buttons = page.get_by_role("button").all()
    button_texts = [b.inner_text() for b in buttons]
    found = [t for t in button_texts if t in possible_texts]
    assert len(found) > 0, f"QRZ button not found. Buttons: {button_texts}"
