"""Layout-contract tests that preserve the desktop dashboard view.

Pixel screenshots are not used: CI runs on Linux and Windows with CDN fonts,
and timestamps change every load. Geometry assertions lock the same view
instead — columns, chrome, and cell contents must stay fully visible inside
the table card at the dashboard's max width (max-w-7xl / 1280px).
"""

from playwright.sync_api import Page, expect

from conftest import _iso_ago, _mock_data, open_dashboard

DESKTOP = {"width": 1280, "height": 800}

COLUMNS = [
    "DX Callsign",
    "DX Location",
    "DXCC",
    "Spotter",
    "Band",
    "Frequency",
    "Mode/Comment",
    "Updated",
    "Source",
]


def _desktop_view_data():
    """Rows shaped like the live dashboard: potential + 3-source UTC spots."""
    mock = _mock_data(num_stations=4)
    fresh = _iso_ago(5)
    mock["stations"][0].update({
        "callsign": "P29YY",
        "dx_country": "Papua New Guinea",
        "dxcc": "163",
        "spotter": "",
        "spotter_country": "",
        "band": "80-10m,160m,201715m",
        "frequency": None,
        "mode": "SSB FT8 CW",
        "comment": "",
        "source": "NG3K",
        "sources": ["NG3K"],
        "potential": True,
        "last_update": fresh,
    })
    mock["stations"][1].update({
        "callsign": "3V8LL",
        "dx_country": "Tunisia",
        "dxcc": "474",
        "spotter": "3V8LL",
        "spotter_country": "Tunisia",
        "band": "17m",
        "frequency": 18.1079,
        "mode": "DATA",
        "source": "DX Summit",
        "sources": ["DX Summit", "HamQTH", "Spothole"],
        "potential": False,
        "last_update": fresh,
    })
    mock["stations"][2].update({
        "callsign": "ZD8GB",
        "dx_country": "Ascension Island",
        "dxcc": "205",
        "spotter": "SP9JZU",
        "spotter_country": "Poland",
        "band": "12m",
        "frequency": 24.9110,
        "mode": "DIGI",
        "source": "DX Summit",
        "sources": ["DX Summit", "HamQTH", "Spothole"],
        "potential": False,
        "last_update": _iso_ago(6),
    })
    mock["stations"][3].update({
        "callsign": "ZD8GB",
        "dx_country": "Ascension Island",
        "dxcc": "205",
        "spotter": "F5BZB",
        "spotter_country": "France",
        "band": "15m",
        "frequency": 21.0900,
        "mode": "FT8",
        "source": "DX Summit",
        "sources": ["DX Summit", "HamQTH", "Spothole"],
        "potential": False,
        "last_update": _iso_ago(7),
    })
    return mock


def _open_desktop(page, data=None):
    page.set_viewport_size(DESKTOP)
    open_dashboard(page, data if data is not None else _desktop_view_data())
    expect(page.locator("table tbody tr").first).to_be_visible()


def _table_card(page):
    return page.locator("div.overflow-hidden").filter(has=page.locator("table"))


def _assert_inside(el, container, label):
    box = el.bounding_box()
    clip = container.bounding_box()
    assert box is not None, label
    assert clip is not None, label
    assert box["x"] >= clip["x"] - 1, label
    assert box["x"] + box["width"] <= clip["x"] + clip["width"] + 1, label
    assert box["y"] >= clip["y"] - 1, label
    assert box["y"] + box["height"] <= clip["y"] + clip["height"] + 1, label


def test_desktop_view_chrome_is_visible(page: Page):
    """Header, stats, search, and pagination stay on screen at 1280px."""
    _open_desktop(page)
    expect(page.get_by_role("link", name="DXpedition Monitor")).to_be_visible()
    expect(page.locator("#tz-slider")).to_be_visible()
    expect(page.get_by_text("Total Stations")).to_be_visible()
    expect(page.get_by_text("Active Now")).to_be_visible()
    expect(page.get_by_text("Last Refresh")).to_be_visible()
    expect(page.get_by_placeholder("Search... (comma=AND pipe=OR)")).to_be_visible()
    expect(page.get_by_text("Rows:")).to_be_visible()
    expect(page.get_by_text("Spot age:")).to_be_visible()
    expect(page.get_by_role("button", name="Previous")).to_be_visible()
    expect(page.get_by_role("button", name="Next")).to_be_visible()


def test_desktop_view_column_order(page: Page):
    """Column order stays Callsign … Source so the Source pills remain last."""
    _open_desktop(page)
    headers = page.get_by_role("columnheader")
    expect(headers).to_have_count(len(COLUMNS))
    for i, name in enumerate(COLUMNS):
        expect(headers.nth(i)).to_have_text(name)


def test_desktop_view_column_headers_fully_visible(page: Page):
    """Every column header is on screen, untruncated, and inside the table card."""
    _open_desktop(page)
    card = _table_card(page)
    for name in COLUMNS:
        header = page.get_by_role("columnheader", name=name)
        expect(header).to_be_visible()
        _assert_inside(header, card, name)
        assert header.evaluate("el => el.scrollWidth <= el.clientWidth + 1"), name


def test_desktop_view_has_no_horizontal_overflow(page: Page):
    """The page and table card do not grow wider than the 1280px viewport."""
    _open_desktop(page)
    metrics = page.evaluate(
        """() => {
            const doc = document.documentElement;
            const table = document.querySelector('table');
            const card = table && table.closest('.overflow-hidden');
            return {
                docScroll: doc.scrollWidth,
                inner: window.innerWidth,
                tableWidth: table ? table.getBoundingClientRect().width : 0,
                cardWidth: card ? card.getBoundingClientRect().width : 0,
            };
        }"""
    )
    assert metrics["docScroll"] <= metrics["inner"] + 1, metrics
    assert metrics["tableWidth"] <= metrics["cardWidth"] + 1, metrics


def test_desktop_view_table_contents_stay_inside_card(page: Page):
    """No header, cell, pill, or label in the table is clipped by the card."""
    _open_desktop(page)
    overflow = page.evaluate(
        """() => {
            const table = document.querySelector('table');
            const card = table && table.closest('.overflow-hidden');
            if (!table || !card) return [{text: 'missing table/card'}];
            const cr = card.getBoundingClientRect();
            const clipped = [];
            for (const el of table.querySelectorAll('th, td, a, span')) {
                const r = el.getBoundingClientRect();
                if (r.width < 1 || r.height < 1) continue;
                if (r.right > cr.right + 1 || r.left < cr.left - 1) {
                    clipped.push({
                        text: (el.textContent || '').trim().slice(0, 48),
                        left: r.left, right: r.right,
                        cardLeft: cr.left, cardRight: cr.right,
                    });
                }
            }
            return clipped;
        }"""
    )
    assert overflow == [], overflow


def test_desktop_view_keeps_screenshot_rows(page: Page):
    """The live-view mix of a potential row and 3-source spots all render."""
    _open_desktop(page)
    rows = page.locator("table tbody tr")
    expect(rows).to_have_count(4)
    expect(page.get_by_role("link", name="P29YY")).to_be_visible()
    expect(page.get_by_role("link", name="3V8LL")).to_be_visible()
    expect(page.get_by_role("link", name="ZD8GB")).to_have_count(2)


def test_desktop_view_source_pills_and_timestamps_not_clipped(page: Page):
    """The Source pills and UTC Updated values from the live view stay fully visible."""
    _open_desktop(page)
    card = _table_card(page)
    row = page.locator("table tbody tr").filter(has_text="3V8LL").first
    expect(row).to_be_visible()
    source_cell = row.locator("td").last
    for name in ("DX Summit", "HamQTH", "Spothole"):
        pill = source_cell.get_by_role("link", name=name, exact=True)
        expect(pill).to_be_visible()
        _assert_inside(pill, card, name)
        assert pill.evaluate("el => el.scrollWidth <= el.clientWidth + 1"), name

    updated = row.locator("td").nth(7)
    expect(updated).to_contain_text("UTC")
    _assert_inside(updated, card, "Updated")
    assert updated.evaluate("el => el.scrollWidth <= el.clientWidth + 1")


def test_desktop_view_potential_row_keeps_badge_and_source(page: Page):
    """Potential rows still show the badge, 'not spotted', and NG3K pill unclipped."""
    _open_desktop(page)
    card = _table_card(page)
    row = page.locator("table tbody tr").filter(has_text="P29YY")
    expect(row.get_by_text("potential", exact=True)).to_be_visible()
    expect(row.get_by_text("not spotted")).to_be_visible()
    pill = row.locator("td").last.get_by_role("link", name="NG3K")
    expect(pill).to_be_visible()
    _assert_inside(pill, card, "NG3K")
    _assert_inside(row.get_by_text("potential", exact=True), card, "potential")
