import json
import pytest
from playwright.sync_api import Page, expect
from conftest import _mock_data


def test_pagination_controls_visible(page: Page):
    """Pagination controls are visible on the dashboard."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data(num_stations=5)),
    ))
    page.goto("http://localhost:8000")
    
    expect(page.get_by_role("button", name="Previous")).to_be_visible()
    expect(page.get_by_role("button", name="Next")).to_be_visible()


def test_row_count_select_works(page: Page):
    """Row count select changes the number of displayed rows."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data(num_stations=10)),
    ))
    page.goto("http://localhost:8000")
    
    # Default is 25
    select = page.get_by_role("combobox").first
    expect(select).to_have_value("25")
    
    # Change to 10
    select.select_option("10")
    expect(select).to_have_value("10")


def test_pagination_entry_count_text(page: Page):
    """Pagination shows correct entry count text."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data(num_stations=10)),
    ))
    page.goto("http://localhost:8000")
    
    # Should show "Showing 1 to 10 of 10 entries"
    expect(page.get_by_text("Showing 1 to 10 of 10 entries")).to_be_visible()


def test_next_page_button_works(page: Page):
    """Clicking Next advances to the next page."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data(num_stations=15)),
    ))
    page.goto("http://localhost:8000")
    
    # Wait for data to load
    expect(page.get_by_text("Total Stations")).to_be_visible()
    
    # Set page size to 10 (first combobox is rows, second is spot age)
    page.get_by_role("combobox").first.select_option("10")
    
    # Wait for page size change to take effect
    expect(page.get_by_text("Showing 1 to 10 of 15 entries")).to_be_visible()
    
    # Click next
    page.get_by_role("button", name="Next").click()
    
    # Entry count should update (15 stations, page size 10 -> page 2 shows 11-15)
    expect(page.get_by_text("Showing 11 to 15 of 15 entries")).to_be_visible()


def test_previous_button_disabled_on_first_page(page: Page):
    """Previous button is disabled when on the first page."""
    page.goto("http://localhost:8000")
    expect(page.get_by_role("button", name="Previous")).to_be_disabled()


def test_next_button_disabled_on_last_page(page: Page):
    """Next button is disabled when on the last page."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data(num_stations=3)),
    ))
    page.goto("http://localhost:8000")
    
    # Set page size to 10 (more than available)
    page.get_by_role("combobox").first.select_option("10")
    
    expect(page.get_by_role("button", name="Next")).to_be_disabled()
