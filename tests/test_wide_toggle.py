"""Wide layout slider contracts.

The Wide control is a tz-style range slider (`#wide-slider`) sharing the UTC
row: left = Normal (max-w-7xl), right = Wide (w-full). Cover placement,
thumb/track clicks (the click-the-thumb gotcha), fill(), persistence, and the
actual layout effect.
"""

import pytest
from playwright.sync_api import Page, expect

from conftest import _mock_data, open_dashboard, open_dashboard_mode


def _state(page):
    return page.evaluate(
        """() => ({
            value: document.querySelector('#wide-slider').value,
            stored: localStorage.getItem('wideMode'),
            wrapper: document.querySelector('#app > div').className,
            tableWidth: document.querySelector('table').getBoundingClientRect().width,
        })"""
    )


def _click_thumb(page, value):
    box = page.locator("#wide-slider").bounding_box()
    x = box["x"] + box["width"] - 8 if value == "1" else box["x"] + 8
    page.mouse.click(x, box["y"] + box["height"] / 2)


def _click_track_end(page, end):
    box = page.locator("#wide-slider").bounding_box()
    x = box["x"] + 2 if end == "left" else box["x"] + box["width"] - 2
    page.mouse.click(x, box["y"] + box["height"] / 2)


def test_wide_slider_present_with_labels(page: Page):
    """Normal/Wide slider renders in the UTC toggle bar."""
    open_dashboard(page)
    expect(page.locator("#wide-slider")).to_be_visible()
    bar = page.locator("#tz-toggle-bar")
    expect(bar).to_contain_text("Normal")
    expect(bar).to_contain_text("Wide")


def test_wide_slider_shares_the_utc_row(page: Page):
    """Both sliders sit on the same row as the Local/UTC control."""
    open_dashboard(page)
    tz_box = page.locator("#tz-slider").bounding_box()
    wide_box = page.locator("#wide-slider").bounding_box()
    bar_box = page.locator("#tz-toggle-bar").bounding_box()
    assert abs(tz_box["y"] - wide_box["y"]) < 2
    assert bar_box["y"] <= tz_box["y"] < bar_box["y"] + bar_box["height"]


def test_old_wide_button_removed(page: Page):
    """The header toolbar no longer carries a Wide toggle button."""
    open_dashboard(page)
    expect(
        page.get_by_role("button", name="Wide enabled")
    ).to_have_count(0)
    expect(
        page.get_by_role("button", name="Wide disabled")
    ).to_have_count(0)


def test_default_is_normal(page: Page):
    """Fresh visitors get the normal (max-w-7xl) layout, slider left."""
    open_dashboard(page)
    expect(page.locator("#wide-slider")).to_have_value("0")
    assert "max-w-7xl" in _state(page)["wrapper"]


def test_thumb_click_enables_wide(page: Page):
    """Clicking the thumb (no native input event) switches to wide."""
    open_dashboard(page)
    _click_thumb(page, "0")
    state = _state(page)
    assert state["value"] == "1"
    assert state["stored"] == "true"
    assert "w-full" in state["wrapper"]
    assert "max-w-7xl" not in state["wrapper"]


def test_thumb_click_disables_wide(page: Page):
    """A second thumb click returns to normal."""
    open_dashboard_mode(page, wide=True, data=_mock_data(num_stations=5))
    expect(page.locator("#wide-slider")).to_have_value("1")
    _click_thumb(page, "1")
    state = _state(page)
    assert state["value"] == "0"
    assert state["stored"] == "false"
    assert "max-w-7xl" in state["wrapper"]


def test_track_click_selects_side(page: Page):
    """Clicking the far end of the track moves the slider to that side."""
    open_dashboard(page)
    _click_track_end(page, "right")
    state = _state(page)
    assert state["value"] == "1"
    assert "w-full" in state["wrapper"]

    _click_track_end(page, "left")
    state = _state(page)
    assert state["value"] == "0"
    assert "max-w-7xl" in state["wrapper"]


def test_fill_api_sets_wide_mode(page: Page):
    """Programmatic fill() works on the wide slider."""
    open_dashboard(page)
    page.locator("#wide-slider").fill("1")
    expect(page.locator("#wide-slider")).to_have_value("1")
    assert "w-full" in _state(page)["wrapper"]


def test_wide_preference_persists_across_reload(page: Page):
    """The wide choice is stored and restored on the next load."""
    open_dashboard(page)
    _click_thumb(page, "0")
    expect(page.locator("#wide-slider")).to_have_value("1")
    page.reload()
    expect(page.locator("#wide-slider")).to_have_value("1")
    assert "w-full" in _state(page)["wrapper"]


def test_wide_mode_actually_widens_the_layout(page: Page):
    """On a large window, wide mode renders a materially wider table."""
    page.set_viewport_size({"width": 1920, "height": 800})
    open_dashboard_mode(page, wide=False, data=_mock_data(num_stations=5))
    normal_width = _state(page)["tableWidth"]
    assert normal_width < 1400  # capped by max-w-7xl

    page.locator("#wide-slider").fill("1")
    expect(page.locator("#wide-slider")).to_have_value("1")
    wide_width = _state(page)["tableWidth"]
    assert wide_width > normal_width + 300


def test_wide_slider_does_not_disturb_utc(page: Page):
    """Toggling wide leaves the UTC preference untouched."""
    open_dashboard(page)
    before = page.evaluate("() => localStorage.getItem('displayUtc')")
    _click_thumb(page, "0")
    _click_thumb(page, "1")
    assert page.evaluate("() => localStorage.getItem('displayUtc')") == before
    expect(page.locator("#tz-slider")).to_have_value("1")
