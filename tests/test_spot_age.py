from playwright.sync_api import Page, expect

from conftest import _iso_ago, _mock_data, open_dashboard


def _aged_mock():
    """Four stations at 5 / 25 / 45 / 90 minutes old."""
    mock = _mock_data(num_stations=4)
    for station, minutes in zip(mock["stations"], (5, 25, 45, 90)):
        station["last_update"] = _iso_ago(minutes)
    return mock


def test_spot_age_filter_default_is_30(page: Page):
    """Spot age filter shows 30 as default on page load."""
    open_dashboard(page, _aged_mock())
    expect(page.get_by_role("combobox").last).to_have_value("30")


def test_spot_age_filter_options(page: Page):
    """Spot age filter has the expected options."""
    open_dashboard(page, _aged_mock())
    expect(page.get_by_text("Spot age:")).to_be_visible()
    select = page.get_by_role("combobox").last
    expect(select.locator("option")).to_have_count(4)
    expect(select.locator("option")).to_have_text(["10", "20", "30", "60"])


def test_spot_age_filter_hides_spots_older_than_selected(page: Page):
    """Changing the spot-age cutoff actually filters table rows."""
    open_dashboard(page, _aged_mock())
    # Default 30 min: 5 and 25 stay, 45 and 90 drop.
    expect(page.get_by_role("cell", name="W1AW")).to_be_visible()
    expect(page.get_by_role("cell", name="VK3EPR")).to_be_visible()
    expect(page.get_by_role("cell", name="P29V")).not_to_be_visible()
    expect(page.get_by_role("cell", name="ZS6DX")).not_to_be_visible()

    page.get_by_role("combobox").last.select_option("10")
    expect(page.get_by_role("cell", name="W1AW")).to_be_visible()
    expect(page.get_by_role("cell", name="VK3EPR")).not_to_be_visible()

    page.get_by_role("combobox").last.select_option("60")
    expect(page.get_by_role("cell", name="W1AW")).to_be_visible()
    expect(page.get_by_role("cell", name="VK3EPR")).to_be_visible()
    expect(page.get_by_role("cell", name="P29V")).to_be_visible()
    expect(page.get_by_role("cell", name="ZS6DX")).not_to_be_visible()
