from playwright.sync_api import Page, expect

from conftest import open_dashboard


def test_dashboard_responsive_on_mobile_width(page: Page):
    """Dashboard layout adapts to narrow viewport."""
    page.set_viewport_size({"width": 375, "height": 667})
    open_dashboard(page)
    expect(page.get_by_role("link", name="DXpedition Monitor")).to_be_visible()
    expect(page.get_by_placeholder("Search... (comma=AND pipe=OR)")).to_be_visible()


def test_dashboard_layout_on_desktop_width(page: Page):
    """Dashboard layout is correct on desktop viewport."""
    page.set_viewport_size({"width": 1280, "height": 800})
    open_dashboard(page)
    expect(page).to_have_title("DXpedition Monitor")
    expect(page.get_by_placeholder("Search... (comma=AND pipe=OR)")).to_be_visible()
