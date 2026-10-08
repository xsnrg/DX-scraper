"""Vertical viewport contracts for the dashboard table.

The table must live in normal page flow: its visible vertical extent is set by
the browser window, and the only thing limiting how many rows render is the
Rows-per-page selection. No fixed-height or max-height element may clip the
table or introduce an inner vertical scrollbar, in either layout mode.
"""

import pytest
from playwright.sync_api import Page, expect

from conftest import _iso_ago, open_dashboard_mode

COUNTRIES = ["USA", "Japan", "Brazil", "Germany", "Australia"]


def _row_data(n):
    """Dashboard payload with `n` unique rows (mock base only holds 15)."""
    stations = []
    for i in range(n):
        country = COUNTRIES[i % len(COUNTRIES)]
        stations.append({
            "callsign": f"N{0 + i:04d}X",
            "dx_country": country,
            "spotter_country": country,
            "spotter": f"W{i:04d}Y",
            "band": "20m",
            "frequency": 14.0 + i * 0.001,
            "mode": "FT8",
            "comment": "",
            "source": "DX Summit",
            "pota_reference": None,
            "sources": ["DX Summit"],
            "last_update": _iso_ago(1),
        })
    return {
        "total_stations": n,
        "active_stations": n,
        "last_refresh": _iso_ago(1),
        "data_sources": ["DX Summit"],
        "stations": stations,
    }


@pytest.mark.parametrize("wide", [False, True])
def test_table_area_has_no_inner_vertical_scrolling(page: Page, wide):
    """No element between the table and <body> vertically clips content."""
    open_dashboard_mode(page, wide, _row_data(30))
    page.get_by_role("combobox").first.select_option("50")
    expect(page.locator("table tbody tr")).to_have_count(30)

    clipped = page.evaluate(
        """() => {
            const table = document.querySelector('table');
            const bad = [];
            let el = table;
            while (el && el !== document.body) {
                const cs = getComputedStyle(el);
                const scrollsY = ['auto', 'scroll'].includes(cs.overflowY);
                const clipsY = cs.overflowY === 'hidden';
                if ((scrollsY || clipsY) && el.scrollHeight > el.clientHeight + 1) {
                    bad.push({
                        tag: el.tagName, cls: String(el.className).slice(0, 60),
                        scrollHeight: el.scrollHeight, clientHeight: el.clientHeight,
                    });
                }
                el = el.parentElement;
            }
            return bad;
        }"""
    )
    assert clipped == [], f"vertically clipping ancestors: {clipped}"


@pytest.mark.parametrize("wide", [False, True])
def test_table_ancestors_have_no_max_height(page: Page, wide):
    """Nothing caps the table's vertical growth except the row count."""
    open_dashboard_mode(page, wide, _row_data(30))
    capped = page.evaluate(
        """() => {
            const table = document.querySelector('table');
            const bad = [];
            let el = table;
            while (el && el !== document.body) {
                const maxH = getComputedStyle(el).maxHeight;
                if (maxH && maxH !== 'none') {
                    bad.push({
                        tag: el.tagName, cls: String(el.className).slice(0, 60),
                        maxHeight: maxH,
                    });
                }
                el = el.parentElement;
            }
            return bad;
        }"""
    )
    assert capped == [], f"max-height capped ancestors: {capped}"


@pytest.mark.parametrize("wide", [False, True])
def test_row_count_limited_only_by_page_size(page: Page, wide):
    """Rendered rows and table height follow the Rows selection, not the window."""
    page.set_viewport_size({"width": 1280, "height": 500})
    open_dashboard_mode(page, wide, _row_data(30))
    rows_select = page.get_by_role("combobox").first

    rows_select.select_option("10")
    expect(page.locator("table tbody tr")).to_have_count(10)
    height10 = page.locator("table").bounding_box()["height"]

    rows_select.select_option("25")
    expect(page.locator("table tbody tr")).to_have_count(25)
    height25 = page.locator("table").bounding_box()["height"]

    rows_select.select_option("50")
    expect(page.locator("table tbody tr")).to_have_count(30)  # only 30 exist
    height50 = page.locator("table").bounding_box()["height"]

    assert height25 > height10
    assert height50 > height25


@pytest.mark.parametrize("wide", [False, True])
def test_table_not_clipped_by_card(page: Page, wide):
    """First and last rows sit inside the table card's vertical bounds."""
    open_dashboard_mode(page, wide, _row_data(30))
    page.get_by_role("combobox").first.select_option("50")
    card = page.locator("div.overflow-hidden").filter(has=page.locator("table"))
    card_box = card.bounding_box()
    rows = page.locator("table tbody tr")
    first = rows.first.bounding_box()
    last = rows.last.bounding_box()
    assert first["y"] >= card_box["y"] - 1
    assert first["y"] + first["height"] <= card_box["y"] + card_box["height"] + 1
    assert last["y"] >= card_box["y"] - 1
    assert last["y"] + last["height"] <= card_box["y"] + card_box["height"] + 1


@pytest.mark.parametrize("wide", [False, True])
@pytest.mark.parametrize("width", [1024, 1280, 1440, 1920])
def test_no_horizontal_scroll_any_mode(page: Page, width, wide):
    """The document never scrolls horizontally, normal or wide layout."""
    page.set_viewport_size({"width": width, "height": 800})
    open_dashboard_mode(page, wide, _row_data(10))
    metrics = page.evaluate(
        """() => ({
            scrollWidth: document.documentElement.scrollWidth,
            inner: window.innerWidth,
        })"""
    )
    assert metrics["scrollWidth"] <= metrics["inner"] + 1, metrics


@pytest.mark.parametrize("wide", [False, True])
def test_full_table_reachable_by_window_scrolling(page: Page, wide):
    """With more rows than fit, the window scrolls — no inner pane traps them."""
    page.set_viewport_size({"width": 1280, "height": 450})
    open_dashboard_mode(page, wide, _row_data(30))
    page.get_by_role("combobox").first.select_option("50")

    # Scrolling the window to the bottom must bring the last row into view.
    page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
    row_box = page.locator("table tbody tr").last.bounding_box()
    viewport = page.viewport_size
    assert row_box is not None and viewport is not None
    row_top_in_view = row_box["y"] <= viewport["height"]
    assert row_top_in_view, (
        f"last row at y={row_box['y']} still below viewport "
        f"height={viewport['height']} after scrolling to bottom"
    )
