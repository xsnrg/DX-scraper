import json
import pytest
from playwright.sync_api import Page, expect
from conftest import _mock_data


def test_column_headers_are_sortable(page: Page):
    """Column headers show sort indicators and are clickable."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data()),
    ))
    page.goto("http://localhost:8000")
    
    # Column headers should be clickable (have cursor-pointer class)
    th_elements = page.locator("th").all()
    th_texts = [th.inner_text() for th in th_elements]
    assert "DX CALLSIGN" in th_texts
    dx_th = page.locator("th").filter(has_text="DX CALLSIGN")
    expect(dx_th).to_have_attribute("class", "px-6 py-4 cursor-pointer hover:bg-slate-600 transition-colors")


def test_sorting_changes_row_order(page: Page):
    """Clicking a column header changes the row order."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data(num_stations=5)),
    ))
    page.goto("http://localhost:8000")
    
    # Get first callsign
    first_callsign = page.locator("table tbody tr").first.get_by_role("link").first.inner_text()
    
    # Click the callsign column header to toggle sort
    page.get_by_role("columnheader", name="DX Callsign").click()
    
    # Row order should have changed
    second_callsign = page.locator("table tbody tr").first.get_by_role("link").first.inner_text()
    assert first_callsign != second_callsign
