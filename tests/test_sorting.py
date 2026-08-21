from playwright.sync_api import Page, expect

from conftest import _mock_data, open_dashboard


def test_column_headers_are_sortable(page: Page):
    """Column headers show sort indicators and are clickable."""
    open_dashboard(page)
    th_texts = [th.inner_text() for th in page.locator("th").all()]
    assert "DX CALLSIGN" in th_texts
    dx_th = page.locator("th").filter(has_text="DX CALLSIGN")
    expect(dx_th).to_have_attribute(
        "class", "px-6 py-4 cursor-pointer hover:bg-slate-600 transition-colors"
    )


def test_sorting_changes_row_order(page: Page):
    """Clicking a column header changes the row order."""
    open_dashboard(page, _mock_data(num_stations=5))
    first_callsign = page.locator("table tbody tr").first.get_by_role("link").first.inner_text()
    page.get_by_role("columnheader", name="DX Callsign").click()
    second_callsign = page.locator("table tbody tr").first.get_by_role("link").first.inner_text()
    assert first_callsign != second_callsign
    assert second_callsign == "JA1RAT"
