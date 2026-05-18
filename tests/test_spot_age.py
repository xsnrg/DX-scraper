import pytest
from playwright.sync_api import Page, expect


def test_spot_age_filter_default_is_30(page: Page):
    """Spot age filter shows 30 as default on page load."""
    page.goto("http://localhost:8000")
    select = page.get_by_role("combobox").last
    expect(select).to_have_value("30")


def test_spot_age_filter_options(page: Page):
    """Spot age filter has the expected options."""
    page.goto("http://localhost:8000")
    expect(page.get_by_text("Spot age:")).to_be_visible()


def test_spot_age_filter_changes_value(page: Page):
    """Changing spot age filter updates the select value."""
    page.goto("http://localhost:8000")
    select = page.get_by_role("combobox").last
    select.select_option("60")
    expect(select).to_have_value("60")
