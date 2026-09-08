from urllib.parse import urlparse

from playwright.sync_api import Page, expect

from conftest import DASHBOARD_URL, _json_fulfill, _mock_data, open_dashboard, stub_dashboard


def test_dashboard_has_correct_title(page: Page):
    """Dashboard page has the correct browser tab title."""
    open_dashboard(page)
    expect(page).to_have_title("DXpedition Monitor")


def test_dashboard_header_section(page: Page):
    """Dashboard renders header with title and action buttons."""
    open_dashboard(page)
    title_link = page.get_by_role("link", name="DXpedition Monitor")
    expect(title_link).to_be_visible()
    expect(title_link).to_have_attribute("href", "https://github.com/xsnrg/DX-scraper")
    expect(page.get_by_text("Tracking of active DX spots")).to_be_visible()


def test_dashboard_stats_cards_render(page: Page):
    """Stats cards appear after data loads."""
    open_dashboard(page)
    expect(page.get_by_text("Total Stations")).to_be_visible()
    expect(page.get_by_text("Active Now")).to_be_visible()
    expect(page.get_by_text("Last Refresh")).to_be_visible()


def test_dashboard_stats_show_correct_values(page: Page):
    """Stats cards display correct counts from data."""
    open_dashboard(page, _mock_data(num_stations=15))
    grid = page.locator("div.grid").first
    expect(grid).to_contain_text("15")


def test_dashboard_loading_state(page: Page):
    """Dashboard shows an error when /data fails to load."""
    stub_dashboard(page)
    page.unroute("**/data*")
    page.route("**/data*", lambda route, request=None: route.abort(error_code="failed")
               if urlparse(route.request.url).path == "/data" else route.fallback())
    page.goto(DASHBOARD_URL)
    expect(page.get_by_text("Failed to load data")).to_be_visible()


def test_dashboard_error_retry(page: Page):
    """Error state shows retry button that re-fetches data."""
    fail = {"on": True}

    def handle_data(route, request=None):
        if urlparse(route.request.url).path != "/data":
            route.fallback()
            return
        if fail["on"]:
            route.abort(error_code="failed")
        else:
            _json_fulfill(route, _mock_data(num_stations=3))

    stub_dashboard(page)
    page.unroute("**/data*")
    page.route("**/data*", handle_data)
    page.goto(DASHBOARD_URL)

    expect(page.get_by_text("Failed to load data")).to_be_visible()
    fail["on"] = False
    page.get_by_text("Retry").click()
    expect(page.get_by_text("Total Stations")).to_be_visible()


def test_refresh_button_visible(page: Page):
    """Refresh button is visible on the dashboard."""
    open_dashboard(page)
    expect(page.get_by_role("button", name="Refresh Data")).to_be_visible()


def test_refresh_button_shows_loading(page: Page):
    """Refresh button shows loading state while fetching."""
    delay = {"on": False}

    def handle_data(route, request=None):
        if urlparse(route.request.url).path != "/data":
            route.fallback()
            return
        if delay["on"]:
            page.wait_for_timeout(600)
        _json_fulfill(route, _mock_data())

    stub_dashboard(page)
    page.unroute("**/data*")
    page.route("**/data*", handle_data)
    page.goto(DASHBOARD_URL)
    expect(page.get_by_role("button", name="Refresh Data")).to_be_visible()
    delay["on"] = True
    page.get_by_role("button", name="Refresh Data").click()
    expect(page.get_by_text("Updating...")).to_be_visible()
    expect(page.get_by_role("button", name="Refresh Data")).to_be_visible()


def test_countdown_text_visible(page: Page):
    """Countdown text is visible under the refresh button."""
    open_dashboard(page)
    expect(page.get_by_text("Refresh in")).to_be_visible()


def test_timezone_slider_visible_at_top(page: Page):
    """Local/UTC slider is rendered at the top of the page."""
    open_dashboard(page)
    slider = page.locator("#tz-slider")
    expect(slider).to_be_visible()
    bar = page.locator("#tz-toggle-bar")
    expect(bar).to_contain_text("Local")
    expect(bar).to_contain_text("UTC")
    header_box = page.locator("header").first.bounding_box()
    slider_box = slider.bounding_box()
    assert slider_box is not None and header_box is not None
    assert slider_box["y"] < header_box["y"]


def test_timezone_slider_defaults_to_utc(page: Page):
    """Times include a UTC suffix when the slider is in the default UTC position."""
    open_dashboard(page)
    expect(page.locator("#tz-slider")).to_have_value("1")
    expect(page.locator("#last-refresh-value")).to_contain_text("UTC")


def test_timezone_slider_toggles_to_local_and_persists(page: Page):
    """Sliding to Local removes the UTC suffix and stores the preference."""
    open_dashboard(page)
    page.locator("#tz-slider").fill("0")
    expect(page.locator("#tz-slider")).to_have_value("0")
    expect(page.locator("#last-refresh-value")).not_to_contain_text("UTC")
    stored = page.evaluate("() => localStorage.getItem('displayUtc')")
    assert stored == "false"

    page.reload()
    expect(page.locator("#tz-slider")).to_have_value("0")
    expect(page.locator("#last-refresh-value")).not_to_contain_text("UTC")
