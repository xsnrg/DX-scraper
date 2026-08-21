from playwright.sync_api import Page, expect

from conftest import _mock_data, open_dashboard


def test_pagination_controls_visible(page: Page):
    """Pagination controls are visible on the dashboard."""
    open_dashboard(page, _mock_data(num_stations=5))
    expect(page.get_by_role("button", name="Previous")).to_be_visible()
    expect(page.get_by_role("button", name="Next")).to_be_visible()


def test_row_count_select_works(page: Page):
    """Row count select changes the number of displayed rows."""
    open_dashboard(page, _mock_data(num_stations=10))
    select = page.get_by_role("combobox").first
    expect(select).to_have_value("25")
    select.select_option("10")
    expect(select).to_have_value("10")


def test_pagination_entry_count_text(page: Page):
    """Pagination shows correct entry count text."""
    open_dashboard(page, _mock_data(num_stations=10))
    expect(page.get_by_text("Showing 1 to 10 of 10 entries")).to_be_visible()


def test_next_page_button_works(page: Page):
    """Clicking Next advances to the next page."""
    open_dashboard(page, _mock_data(num_stations=15))
    expect(page.get_by_text("Total Stations")).to_be_visible()
    page.get_by_role("combobox").first.select_option("10")
    expect(page.get_by_text("Showing 1 to 10 of 15 entries")).to_be_visible()
    page.get_by_role("button", name="Next").click()
    expect(page.get_by_text("Showing 11 to 15 of 15 entries")).to_be_visible()


def test_previous_button_disabled_on_first_page(page: Page):
    """Previous button is disabled when on the first page."""
    open_dashboard(page)
    expect(page.get_by_role("button", name="Previous")).to_be_disabled()


def test_next_button_disabled_on_last_page(page: Page):
    """Next button is disabled when on the last page."""
    open_dashboard(page, _mock_data(num_stations=3))
    page.get_by_role("combobox").first.select_option("10")
    expect(page.get_by_role("button", name="Next")).to_be_disabled()
