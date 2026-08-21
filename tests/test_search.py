from playwright.sync_api import Page, expect

from conftest import _mock_data, open_dashboard


def test_search_input_placeholder(page: Page):
    """Search input shows correct placeholder text."""
    open_dashboard(page)
    expect(page.get_by_placeholder("Search... (comma=AND pipe=OR)")).to_be_visible()


def test_search_filters_stations(page: Page):
    """Typing in search keeps matching rows and hides the rest."""
    open_dashboard(page, _mock_data(num_stations=5))
    search = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search.fill("W1AW")
    expect(page.get_by_role("cell", name="W1AW")).to_be_visible()
    expect(page.get_by_role("cell", name="VK3EPR")).not_to_be_visible()
    expect(page.get_by_role("cell", name="P29V")).not_to_be_visible()


def test_search_clear_button_appears(page: Page):
    """Clear (X) button appears when search has text."""
    open_dashboard(page)
    page.get_by_placeholder("Search... (comma=AND pipe=OR)").fill("test")
    expect(page.get_by_title("Clear search")).to_be_visible()


def test_search_clear_button_disappears_when_empty(page: Page):
    """Clear button disappears when search is cleared."""
    open_dashboard(page)
    page.get_by_placeholder("Search... (comma=AND pipe=OR)").fill("test")
    clear_btn = page.get_by_title("Clear search")
    expect(clear_btn).to_be_visible()
    clear_btn.click()
    expect(clear_btn).to_be_hidden()


def test_search_clear_button_clears_input(page: Page):
    """Clicking clear button empties the search input."""
    open_dashboard(page)
    search = page.get_by_placeholder("Search... (comma=AND pipe=OR)")
    search.fill("test")
    page.get_by_title("Clear search").click()
    expect(search).to_have_value("")


def test_search_pipe_or_filtering(page: Page):
    """Pipe character in search acts as OR operator."""
    open_dashboard(page, _mock_data(num_stations=5))
    page.get_by_placeholder("Search... (comma=AND pipe=OR)").fill("USA|Australia")
    expect(page.get_by_role("cell", name="W1AW")).to_be_visible()
    expect(page.get_by_role("cell", name="VK3EPR")).to_be_visible()
    expect(page.get_by_role("cell", name="P29V")).not_to_be_visible()
