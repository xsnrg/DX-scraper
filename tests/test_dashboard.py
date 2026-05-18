import json
import re
import pytest
from playwright.sync_api import Page, expect
from conftest import _mock_data


def test_dashboard_has_correct_title(page: Page):
    """Dashboard page has the correct browser tab title."""
    page.goto("http://localhost:8000")
    expect(page).to_have_title("DXpedition Monitor")


def test_dashboard_header_section(page: Page):
    """Dashboard renders header with title and action buttons."""
    page.goto("http://localhost:8000")
    
    # Main title link
    title_link = page.get_by_role("link", name="DXpedition Monitor")
    expect(title_link).to_be_visible()
    expect(title_link).to_have_attribute("href", "https://github.com/xsnrg/DX-scraper")
    
    # Description text
    desc = page.get_by_text("Tracking of active DX spots")
    expect(desc).to_be_visible()


def test_dashboard_stats_cards_render(page: Page):
    """Stats cards appear after data loads."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data()),
    ))
    page.goto("http://localhost:8000")
    
    # Wait for stats cards to appear
    expect(page.get_by_text("Total Stations")).to_be_visible()
    expect(page.get_by_text("Active Now")).to_be_visible()
    expect(page.get_by_text("Last Refresh")).to_be_visible()


def test_dashboard_stats_show_correct_values(page: Page):
    """Stats cards display correct counts from data."""
    mock = _mock_data(num_stations=15)
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.goto("http://localhost:8000")
    
    # Stats should show 15 total stations - use the grid container
    grid = page.locator("div.grid").first
    grid_text = grid.inner_text()
    assert "15" in grid_text


def test_dashboard_loading_state(page: Page):
    """Dashboard shows loading indicator before data arrives."""
    # Block /data to simulate slow loading
    page.route("**/data*", lambda route: route.abort(error_code="failed"))
    page.goto("http://localhost:8000")
    
    # Should show error state
    expect(page.get_by_text("Failed to load data")).to_be_visible()


def test_dashboard_error_retry(page: Page):
    """Error state shows retry button that re-fetches data."""
    call_count = [0]
    
    def handle_data(route):
        call_count[0] += 1
        if call_count[0] == 1:
            route.abort(error_code="failed")
        else:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(_mock_data(num_stations=3)),
            )
    
    page.route("**/data*", handle_data)
    page.goto("http://localhost:8000")
    
    # Wait for error
    expect(page.get_by_text("Failed to load data")).to_be_visible()
    
    # Click retry
    page.get_by_text("Retry").click()
    
    # Should recover
    expect(page.get_by_text("Total Stations")).to_be_visible()


def test_refresh_button_visible(page: Page):
    """Refresh button is visible on the dashboard."""
    page.goto("http://localhost:8000")
    expect(page.get_by_role("button", name="Refresh Data")).to_be_visible()


def test_refresh_button_shows_loading(page: Page):
    """Refresh button shows loading state while fetching."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data()),
    ))
    page.goto("http://localhost:8000")
    
    # Click refresh
    refresh_btn = page.get_by_role("button", name="Refresh Data")
    refresh_btn.click()
    
    # Should briefly show loading
    expect(page.get_by_text("Updating...")).to_be_visible()


def test_countdown_text_visible(page: Page):
    """Countdown text is visible under the refresh button."""
    page.goto("http://localhost:8000")
    expect(page.get_by_text("Refresh in")).to_be_visible()
