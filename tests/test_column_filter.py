from playwright.sync_api import Page, expect

from conftest import open_dashboard


def test_clicking_band_appends_to_search(page: Page):
    """Clicking a band value in the table appends it to the search box."""
    open_dashboard(page)
    band_span = page.locator("td span.cursor-pointer").first
    band_text = band_span.inner_text()
    band_span.click()
    search_val = page.get_by_placeholder("Search... (comma=AND pipe=OR)").input_value()
    assert band_text in search_val


def test_clicking_mode_appends_to_search(page: Page):
    """Clicking a mode value appends it to the search box."""
    open_dashboard(page)
    mode_span = page.locator("td span.cursor-pointer").nth(1)
    mode_text = mode_span.inner_text()
    mode_span.click()
    search_val = page.get_by_placeholder("Search... (comma=AND pipe=OR)").input_value()
    assert mode_text in search_val


def test_clicking_dx_location_appends_to_search(page: Page):
    """Clicking a DX location appends it to the search box."""
    open_dashboard(page)
    dx_spans = page.locator("td").nth(1).locator("span.cursor-pointer")
    dx_text = dx_spans.first.inner_text()
    dx_spans.first.click()
    search_val = page.get_by_placeholder("Search... (comma=AND pipe=OR)").input_value()
    assert dx_text in search_val
