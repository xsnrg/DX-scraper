import re

from playwright.sync_api import Page, expect

from conftest import _mock_data, open_dashboard, qrz_ready_kwargs


def _wanted_stations():
    mock = _mock_data(num_stations=5)
    mapping = {
        "W1AW": ("United States", "291", "DX Summit"),
        "VK3EPR": ("Australia", "50", "DX Cluster"),
        "ZS6DX": ("South Africa", "197", "DX Summit"),
        "JA1RAT": ("Japan", "339", "DX Cluster"),
    }
    for s in mock["stations"]:
        if s["callsign"] in mapping:
            country, dxcc, source = mapping[s["callsign"]]
            s["dx_country"] = country
            s["dxcc"] = dxcc
            s["source"] = source
    return mock


def test_wanted_button_visible_on_dashboard(page: Page):
    """Wanted toggle button is visible on the dashboard."""
    open_dashboard(page, **qrz_ready_kwargs())
    expect(page.get_by_role("button", name=re.compile("Wanted"))).to_be_visible()


def test_wanted_button_highlights_stations_not_in_qrz_cache(page: Page):
    """Enabling Wanted highlights rows whose DXCC is not in the QRZ cache."""
    open_dashboard(
        page,
        _wanted_stations(),
        **qrz_ready_kwargs(dxcc_numbers=["291", "50"]),
    )
    expect(page.get_by_text("Total Stations")).to_be_visible()
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    expect(page.get_by_role("button", name=re.compile("Wanted enabled"))).to_be_visible()

    w1aw = page.locator("tr").filter(has_text="W1AW").first.get_attribute("class") or ""
    assert "bg-red-500/30" not in w1aw, f"W1AW (DXCC 291 in cache) should not be red: {w1aw}"

    vk = page.locator("tr").filter(has_text="VK3EPR").first.get_attribute("class") or ""
    assert "bg-red-500/30" not in vk, f"VK3EPR (DXCC 50 in cache) should not be red: {vk}"

    zs = page.locator("tr").filter(has_text="ZS6DX").first.get_attribute("class") or ""
    assert "bg-red-500/30" in zs, f"ZS6DX (DXCC 197 not in cache) should be red: {zs}"

    ja = page.locator("tr").filter(has_text="JA1RAT").first.get_attribute("class") or ""
    assert "bg-red-500/30" in ja, f"JA1RAT (DXCC 339 not in cache) should be red: {ja}"


def test_wanted_button_ignores_pota_stations(page: Page):
    """Wanted filter does not highlight POTA stations even when DXCC is not in cache."""
    mock = _mock_data(num_stations=3)
    for s in mock["stations"]:
        if s["source"] == "POTA":
            s["dx_country"] = "Palau"
            s["dxcc"] = "22"
        else:
            s["dxcc"] = ""
    open_dashboard(page, mock, **qrz_ready_kwargs())
    expect(page.get_by_text("Total Stations")).to_be_visible()
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    classes = page.locator("tr").filter(has_text="P29V").first.get_attribute("class") or ""
    assert "bg-red-500/30" not in classes, f"POTA station should not be highlighted: {classes}"


def test_wanted_button_normalizes_leading_zeros(page: Page):
    """Wanted filter correctly normalizes DXCC numbers with leading zeros."""
    mock = _mock_data(num_stations=3)
    for s in mock["stations"]:
        if s["callsign"] == "W1AW":
            s["dxcc"] = "0291"
        elif s["callsign"] == "VK3EPR":
            s["dxcc"] = "0050"
        else:
            s["dxcc"] = ""
    open_dashboard(page, mock, **qrz_ready_kwargs(dxcc_numbers=["291"]))
    expect(page.get_by_text("Total Stations")).to_be_visible()
    page.get_by_role("button", name=re.compile("Wanted")).first.click()

    w1aw = page.locator("tr").filter(has_text="W1AW").first.get_attribute("class") or ""
    assert "bg-red-500/30" not in w1aw, f"W1AW (0291 -> 291 in cache) should not be red: {w1aw}"

    vk = page.locator("tr").filter(has_text="VK3EPR").first.get_attribute("class") or ""
    assert "bg-red-500/30" in vk, f"VK3EPR (0050 -> 50 not in cache) should be red: {vk}"


def test_wanted_row_color_is_red(page: Page):
    """Wanted rows use bg-red-500/30 class (not orange or other colors)."""
    mock = _mock_data(num_stations=3)
    for s in mock["stations"]:
        s["dxcc"] = "50" if s["callsign"] == "VK3EPR" else ""
    open_dashboard(page, mock, **qrz_ready_kwargs())
    expect(page.get_by_text("Total Stations")).to_be_visible()
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    classes = page.locator("tr").filter(has_text="VK3EPR").first.get_attribute("class") or ""
    assert "bg-red-500/30" in classes, f"VK3EPR should have bg-red-500/30, got: {classes}"
    assert "bg-orange" not in classes, f"VK3EPR should NOT have orange class, got: {classes}"


def test_only_wanted_shows_only_wanted_rows(page: Page):
    """Only wanted mode shows only stations with DXCC numbers not in QRZ cache."""
    open_dashboard(
        page,
        _wanted_stations(),
        **qrz_ready_kwargs(dxcc_numbers=["291", "50"]),
    )
    expect(page.get_by_text("Total Stations")).to_be_visible()
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    expect(page.get_by_role("button", name=re.compile("Only wanted"))).to_be_visible()

    expect(page.locator("tr").filter(has_text="ZS6DX").first).to_be_visible()
    expect(page.locator("tr").filter(has_text="JA1RAT").first).to_be_visible()
    expect(page.locator("tr").filter(has_text="W1AW").first).not_to_be_visible()
    expect(page.locator("tr").filter(has_text="VK3EPR").first).not_to_be_visible()


def test_wanted_button_color_changes(page: Page):
    """Wanted button color changes from emerald to red when enabled."""
    open_dashboard(page, _mock_data(num_stations=3), **qrz_ready_kwargs(dxcc_numbers=[], cache_data=[], all_data=[]))
    expect(page.get_by_text("Total Stations")).to_be_visible()

    button = page.get_by_role("button", name=re.compile("Wanted")).first
    classes = button.get_attribute("class") or ""
    assert "bg-emerald-600" in classes, f"Button should be emerald when disabled, got: {classes}"

    button.click()
    expect(page.get_by_role("button", name=re.compile("Wanted enabled"))).to_be_visible()
    classes = page.get_by_role("button", name=re.compile("Wanted enabled")).first.get_attribute("class") or ""
    assert "bg-red-500" in classes, f"Button should be red when enabled, got: {classes}"

    page.get_by_role("button", name=re.compile("Wanted enabled")).first.click()
    expect(page.get_by_role("button", name=re.compile("Only wanted"))).to_be_visible()
    classes = page.get_by_role("button", name=re.compile("Only wanted")).first.get_attribute("class") or ""
    assert "bg-red-500" in classes, f"Button should be red in only wanted mode, got: {classes}"

    page.get_by_role("button", name=re.compile("Only wanted")).first.click()
    expect(page.get_by_role("button", name=re.compile("Wanted disabled"))).to_be_visible()
    classes = page.get_by_role("button", name=re.compile("Wanted disabled")).first.get_attribute("class") or ""
    assert "bg-emerald-600" in classes, f"Button should be emerald when disabled, got: {classes}"


def test_wanted_icon_changes_with_mode(page: Page):
    """Wanted button icon changes: half-stroke -> star -> bullseye -> half-stroke."""
    open_dashboard(page, _mock_data(num_stations=3), **qrz_ready_kwargs())
    expect(page.get_by_text("Total Stations")).to_be_visible()

    expect(page.locator("i.fas.fa-star-half-stroke")).to_be_visible()
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    expect(page.get_by_role("button", name=re.compile("Wanted enabled"))).to_be_visible()
    expect(page.locator("i.fas.fa-star")).to_be_visible()

    page.get_by_role("button", name=re.compile("Wanted enabled")).first.click()
    expect(page.get_by_role("button", name=re.compile("Only wanted"))).to_be_visible()
    expect(page.locator("i.fas.fa-crosshairs")).to_be_visible()

    page.get_by_role("button", name=re.compile("Only wanted")).first.click()
    expect(page.get_by_role("button", name=re.compile("Wanted disabled"))).to_be_visible()
    expect(page.locator("i.fas.fa-star-half-stroke")).to_be_visible()
