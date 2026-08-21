"""Playwright tests for NG3K potential spots in the dashboard table."""
import re

from playwright.sync_api import Page, expect

from conftest import _iso_ago, _mock_data, open_dashboard, qrz_ready_kwargs


def _with_potential(callsign="RI1FJL", dxcc="61", country="Franz Josef Land"):
    mock = _mock_data(num_stations=3)
    mock["stations"].append({
        "callsign": callsign,
        "dx_country": country,
        "dxcc": dxcc,
        "spotter_country": "",
        "spotter": "",
        "band": "160-10m",
        "frequency": None,
        "mode": "CW SSB",
        "comment": "",
        "source": "NG3K",
        "sources": ["NG3K"],
        "pota_reference": None,
        "potential": True,
        "last_update": _iso_ago(90),
    })
    mock["total_stations"] = len(mock["stations"])
    mock["active_stations"] = len(mock["stations"])
    return mock


def test_potential_badge_and_not_spotted(page: Page):
    """Potential rows show a marker and 'not spotted' instead of a timestamp."""
    open_dashboard(page, _with_potential())
    row = page.locator("tr").filter(has_text="RI1FJL")
    expect(row).to_be_visible()
    expect(row.get_by_text("potential")).to_be_visible()
    expect(row.get_by_text("not spotted")).to_be_visible()
    live = page.locator("tr").filter(has_text="W1AW")
    expect(live.get_by_text("potential")).to_have_count(0)
    # Badge is stacked under the call, not inline beside it.
    badge_box = row.get_by_text("potential", exact=True).bounding_box()
    call_box = row.get_by_role("link", name="RI1FJL").bounding_box()
    assert badge_box and call_box
    assert badge_box["y"] >= call_box["y"] + call_box["height"] - 1
    expect(row.get_by_text("160-10m")).to_be_visible()
    expect(row.get_by_text("CW SSB")).to_be_visible()



def test_potential_survives_spot_age_filter(page: Page):
    """Potential spots are exempt from the spot-age cutoff."""
    open_dashboard(page, _with_potential())
    page.get_by_role("combobox").last.select_option("10")
    expect(page.locator("tr").filter(has_text="RI1FJL")).to_be_visible()
    expect(page.locator("tr").filter(has_text="W1AW")).to_be_visible()


def test_wanted_highlights_potential_needed_dxcc(page: Page):
    """Wanted still paints a potential row red when the DXCC is unconfirmed."""
    open_dashboard(
        page,
        _with_potential(),
        **qrz_ready_kwargs(dxcc_numbers=["291"]),
    )
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    classes = page.locator("tr").filter(has_text="RI1FJL").first.get_attribute("class") or ""
    assert "bg-red-500/30" in classes
    w1aw = page.locator("tr").filter(has_text="W1AW").first.get_attribute("class") or ""
    assert "bg-red-500/30" not in w1aw


def test_only_wanted_keeps_unconfirmed_potential(page: Page):
    """Only-wanted mode keeps a potential row whose DXCC is not in the log."""
    open_dashboard(
        page,
        _with_potential(),
        **qrz_ready_kwargs(dxcc_numbers=["291"]),
    )
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    page.get_by_role("button", name=re.compile("Wanted enabled")).first.click()
    expect(page.get_by_role("button", name=re.compile("Only wanted"))).to_be_visible()
    expect(page.locator("tr").filter(has_text="RI1FJL")).to_be_visible()
    expect(page.locator("tr").filter(has_text="W1AW")).to_have_count(0)
