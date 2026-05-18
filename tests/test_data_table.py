import json
import pytest
from playwright.sync_api import Page, expect
from conftest import _mock_data


def test_data_table_has_correct_columns(page: Page):
    """Data table renders with all expected column headers."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data()),
    ))
    page.goto("http://localhost:8000")
    
    columns = ["DX Callsign", "DX Location", "Spotter", "Band", "Frequency", "Mode/Comment", "Updated", "Source"]
    for col in columns:
        expect(page.get_by_role("columnheader", name=col)).to_be_visible()


def test_data_table_shows_station_rows(page: Page):
    """Data table displays station rows with correct data."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data(num_stations=5)),
    ))
    page.goto("http://localhost:8000")
    
    # Should show 5 rows
    rows = page.locator("table tbody tr").all()
    assert len(rows) == 5
    
    # First row should be W1AW
    expect(page.get_by_role("cell", name="W1AW")).to_be_visible()


def test_data_table_callsigns_are_links(page: Page):
    """Callsigns in the table are clickable links to QRZ."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data()),
    ))
    page.goto("http://localhost:8000")
    
    # Find a callsign link
    callsign_link = page.get_by_role("link", name="W1AW")
    expect(callsign_link).to_be_visible()
    expect(callsign_link).to_have_attribute("href", "https://www.qrz.com/db/W1AW")


def test_data_table_frequencies_displayed(page: Page):
    """Frequency column shows values in MHz format."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data()),
    ))
    page.goto("http://localhost:8000")
    
    # Should show frequency with MHz suffix
    expect(page.get_by_text("7.0740 MHz")).to_be_visible()


def test_data_table_source_badges(page: Page):
    """Source column shows colored badges with source names."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data()),
    ))
    page.goto("http://localhost:8000")
    
    expect(page.get_by_text("DX Summit").first).to_be_visible()
    expect(page.get_by_text("DX Cluster").first).to_be_visible()


def test_data_table_empty_state(page: Page):
    """Table shows empty state message when no stations match."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"stations": [], "summary": {"total_stations": 0, "active_stations": 0, "last_refresh": ""}}),
    ))
    page.goto("http://localhost:8000")
    
    expect(page.get_by_text("No stations found matching your criteria.")).to_be_visible()
