from playwright.sync_api import Page, expect

from conftest import _mock_data, open_dashboard


def test_data_table_has_correct_columns(page: Page):
    """Data table renders with all expected column headers."""
    open_dashboard(page)
    columns = [
        "DX Callsign", "DX Location", "Spotter", "Band",
        "Frequency", "Mode/Comment", "Updated", "Source",
    ]
    for col in columns:
        expect(page.get_by_role("columnheader", name=col)).to_be_visible()


def test_data_table_shows_station_rows(page: Page):
    """Data table displays station rows with correct data."""
    open_dashboard(page, _mock_data(num_stations=5))
    rows = page.locator("table tbody tr").all()
    assert len(rows) == 5
    expect(page.get_by_role("cell", name="W1AW")).to_be_visible()


def test_data_table_callsigns_are_links(page: Page):
    """Callsigns in the table are clickable links to QRZ."""
    open_dashboard(page)
    callsign_link = page.get_by_role("link", name="W1AW")
    expect(callsign_link).to_be_visible()
    expect(callsign_link).to_have_attribute("href", "https://www.qrz.com/db/W1AW")


def test_data_table_frequencies_displayed(page: Page):
    """Frequency column shows values in MHz format."""
    open_dashboard(page)
    expect(page.get_by_text("7.0740 MHz")).to_be_visible()


def test_data_table_source_badges(page: Page):
    """Source column shows colored badges with source names."""
    open_dashboard(page)
    expect(page.get_by_text("DX Summit").first).to_be_visible()
    expect(page.get_by_text("DX Cluster").first).to_be_visible()


def test_data_table_wraps_multiple_source_badges(page: Page):
    """Each source is its own badge on one line so names are not clipped."""
    mock = _mock_data(num_stations=2)
    mock["stations"][0]["source"] = "DX Summit"
    mock["stations"][0]["sources"] = ["DX Summit", "HamQTH", "Spothole"]
    mock["stations"][1]["source"] = "NG3K"
    mock["stations"][1]["sources"] = ["NG3K"]
    open_dashboard(page, mock)
    rows = page.locator("table tbody tr")
    source_cell = rows.nth(0).locator("td").last
    expect(source_cell.get_by_text("DX Summit", exact=True)).to_be_visible()
    expect(source_cell.get_by_text("HamQTH", exact=True)).to_be_visible()
    expect(source_cell.get_by_text("Spothole", exact=True)).to_be_visible()
    expect(source_cell.get_by_text("DX Summit, HamQTH")).to_have_count(0)

    multi_h = rows.nth(0).bounding_box()["height"]
    single_h = rows.nth(1).bounding_box()["height"]
    assert abs(multi_h - single_h) <= 1

    cell_box = source_cell.bounding_box()
    for name in ("DX Summit", "HamQTH", "Spothole"):
        badge_box = source_cell.get_by_text(name, exact=True).bounding_box()
        assert badge_box["x"] + badge_box["width"] <= cell_box["x"] + cell_box["width"] + 1
        assert badge_box["y"] + badge_box["height"] <= cell_box["y"] + cell_box["height"] + 1


def test_data_table_multiple_spots_same_callsign(page: Page):
    """A DXpedition callsign can appear on more than one band/mode at once."""
    mock = _mock_data(num_stations=2)
    extra = dict(mock["stations"][0])
    extra["band"] = "20m"
    extra["frequency"] = 14.023
    extra["mode"] = "CW"
    extra["comment"] = "20m station"
    mock["stations"].append(extra)
    mock["total_stations"] = len(mock["stations"])
    mock["active_stations"] = len(mock["stations"])
    open_dashboard(page, mock)
    rows = page.locator("tr").filter(has_text="W1AW")
    expect(rows).to_have_count(2)
    expect(rows.filter(has_text="40m")).to_be_visible()
    expect(rows.filter(has_text="20m")).to_be_visible()
    expect(rows.filter(has_text="CW")).to_be_visible()
    expect(rows.filter(has_text="SSB")).to_be_visible()


def test_data_table_empty_state(page: Page):
    """Table shows empty state message when no stations match."""
    open_dashboard(page, _mock_data(num_stations=0))
    expect(page.get_by_text("No stations found matching your criteria.")).to_be_visible()
