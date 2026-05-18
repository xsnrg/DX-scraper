import json
import pytest
from playwright.sync_api import Page, expect
from conftest import _mock_data


def test_search_input_placeholder(page: Page):
    """Search input shows correct placeholder text."""
    page.goto("http://localhost:8000")
    search = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    expect(search).to_be_visible()


def test_search_filters_stations(page: Page):
    """Typing in search filters table rows."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data(num_stations=5)),
    ))
    page.goto("http://localhost:8000")
    
    # Count initial rows
    initial_rows = page.locator("table tbody tr").count()
    
    # Type search
    search = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search.fill("USA")
    
    # Rows should be filtered (only USA stations)
    filtered_rows = page.locator("table tbody tr").count()
    assert filtered_rows < initial_rows


def test_search_clear_button_appears(page: Page):
    """Clear (X) button appears when search has text."""
    page.goto("http://localhost:8000")
    search = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search.fill("test")
    
    clear_btn = page.get_by_title("Clear search")
    expect(clear_btn).to_be_visible()


def test_search_clear_button_disappears_when_empty(page: Page):
    """Clear button disappears when search is cleared."""
    page.goto("http://localhost:8000")
    search = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search.fill("test")
    
    clear_btn = page.get_by_title("Clear search")
    expect(clear_btn).to_be_visible()
    
    clear_btn.click()
    expect(clear_btn).to_be_hidden()


def test_search_clear_button_clears_input(page: Page):
    """Clicking clear button empties the search input."""
    page.goto("http://localhost:8000")
    search = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search.fill("test")
    
    page.get_by_title("Clear search").click()
    expect(search).to_have_value("")


def test_search_pipe_or_filtering(page: Page):
    """Pipe character in search acts as OR operator."""
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(_mock_data(num_stations=5)),
    ))
    page.goto("http://localhost:8000")
    
    search = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search.fill("USA|Australia")
    
    # Should find stations matching either term
    rows = page.locator("table tbody tr").all()
    assert len(rows) > 0
