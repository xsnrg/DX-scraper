"""UTC slider (Local/UTC) behavior contracts.

Regression cover for the reported bug where clicking the white thumb did
nothing: a range input fires no `input` event when the thumb is clicked, so
the app must toggle on such clicks itself. Track clicks, drags, programmatic
fill(), persistence, and the rendered timestamp format are all covered.
"""

import pytest
from playwright.sync_api import Page, expect

from conftest import open_dashboard


def _state(page):
    return page.evaluate(
        """() => ({
            value: document.querySelector('#tz-slider').value,
            stored: localStorage.getItem('displayUtc'),
            refresh: document.querySelector('#last-refresh-value').textContent.trim(),
        })"""
    )


def _click_thumb(page, value):
    """Click the center of the thumb at its current 0/1 position."""
    box = page.locator("#tz-slider").bounding_box()
    x = box["x"] + box["width"] - 8 if value == "1" else box["x"] + 8
    page.mouse.click(x, box["y"] + box["height"] / 2)


def _click_track_end(page, end):
    """Click near the far edge of the track (away from the thumb)."""
    box = page.locator("#tz-slider").bounding_box()
    x = box["x"] + 2 if end == "left" else box["x"] + box["width"] - 2
    page.mouse.click(x, box["y"] + box["height"] / 2)


def test_utc_slider_defaults_to_utc(page: Page):
    """Fresh visitors see UTC: slider right, suffix present."""
    open_dashboard(page)
    expect(page.locator("#tz-slider")).to_have_value("1")
    assert _state(page)["refresh"].endswith("UTC")


def test_clicking_thumb_toggles_to_local(page: Page):
    """Clicking the white thumb (no native input event) switches to Local."""
    open_dashboard(page)
    _click_thumb(page, "1")
    state = _state(page)
    assert state["value"] == "0"
    assert state["stored"] == "false"
    assert not state["refresh"].endswith("UTC")


def test_clicking_thumb_toggles_back_to_utc(page: Page):
    """A second thumb click returns to UTC."""
    open_dashboard(page)
    _click_thumb(page, "1")
    expect(page.locator("#tz-slider")).to_have_value("0")
    _click_thumb(page, "0")
    state = _state(page)
    assert state["value"] == "1"
    assert state["stored"] == "true"
    assert state["refresh"].endswith("UTC")


def test_clicking_track_side_selects_side(page: Page):
    """Clicking the opposite end of the track moves the slider there."""
    open_dashboard(page)
    _click_track_end(page, "left")
    expect(page.locator("#tz-slider")).to_have_value("0")
    assert not _state(page)["refresh"].endswith("UTC")

    _click_track_end(page, "right")
    expect(page.locator("#tz-slider")).to_have_value("1")
    assert _state(page)["refresh"].endswith("UTC")


def test_dragging_thumb_works(page: Page):
    """Dragging the thumb across the track still toggles without double-firing."""
    open_dashboard(page)
    box = page.locator("#tz-slider").bounding_box()
    page.mouse.move(box["x"] + box["width"] - 8, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + 8, box["y"] + box["height"] / 2, steps=5)
    page.mouse.up()
    # Drag reached 0; the click-toggle must NOT have flipped it back to 1.
    assert _state(page)["value"] == "0"
    assert _state(page)["stored"] == "false"


def test_fill_api_still_works(page: Page):
    """Programmatic fill() (the old test path) keeps working."""
    open_dashboard(page)
    page.locator("#tz-slider").fill("0")
    expect(page.locator("#tz-slider")).to_have_value("0")
    assert not _state(page)["refresh"].endswith("UTC")


def test_utc_preference_persists_across_reload(page: Page):
    """The Local choice is stored and restored on the next load."""
    open_dashboard(page)
    _click_thumb(page, "1")
    expect(page.locator("#tz-slider")).to_have_value("0")
    page.reload()
    expect(page.locator("#tz-slider")).to_have_value("0")
    assert not _state(page)["refresh"].endswith("UTC")


def test_utc_toggle_updates_all_timestamps(page: Page):
    """Flipping the slider changes the format of the table's Updated column."""
    open_dashboard(page)
    utc_text = page.locator("table tbody td").nth(7).inner_text()
    assert "UTC" in utc_text

    _click_thumb(page, "1")
    local_text = page.locator("table tbody td").nth(7).inner_text()
    assert "UTC" not in local_text
    assert local_text and local_text != utc_text
