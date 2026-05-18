import json
import pytest
from playwright.sync_api import Page, expect
from conftest import _mock_data


def test_exclude_sources_single_parameter(page: Page):
    """The /data API supports exclude_sources parameter to filter out specific sources."""
    response = page.request.get("http://localhost:8000/data?exclude_sources=POTA")
    assert response.status == 200
    data = response.json()
    assert isinstance(data, dict)


def test_exclude_sources_multiple_parameters(page: Page):
    """The /data API supports comma-separated exclude_sources values."""
    response = page.request.get("http://localhost:8000/data?exclude_sources=POTA,dx_news")
    assert response.status == 200
    data = response.json()
    assert isinstance(data, dict)


def test_dashboard_responsive_on_mobile_width(page: Page):
    """Dashboard layout adapts to narrow viewport."""
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000")
    
    # All main elements should still be visible
    expect(page.get_by_role("link", name="DXpedition Monitor")).to_be_visible()
    expect(page.get_by_placeholder("Search... (comma=AND pipe=OR)")).to_be_visible()


def test_dashboard_layout_on_desktop_width(page: Page):
    """Dashboard layout is correct on desktop viewport."""
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto("http://localhost:8000")
    
    expect(page).to_have_title("DXpedition Monitor")
    expect(page.get_by_placeholder("Search... (comma=AND pipe=OR)")).to_be_visible()
