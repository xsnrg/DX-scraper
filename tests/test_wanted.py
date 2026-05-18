import json
import re
import pytest
from playwright.sync_api import Page, expect
from conftest import _mock_data


def test_wanted_button_visible_on_dashboard(page: Page):
    """Wanted toggle button is visible on the dashboard."""
    page.goto("http://localhost:8000")
    buttons = page.get_by_role("button").all()
    button_texts = [b.inner_text() for b in buttons]
    found = [t for t in button_texts if "Wanted" in t]
    assert len(found) > 0, f"Wanted button not found. Buttons: {button_texts}"


def test_wanted_button_highlights_stations_not_in_qrz_cache(page: Page):
    """Enabling Wanted filter highlights rows with DXCC numbers not in QRZ cache with red class."""
    mock = _mock_data(num_stations=5)
    # Set DXCC numbers using only non-POTA stations from mock: W1AW, VK3EPR, ZS6DX, JA1RAT
    for s in mock["stations"]:
        if s["callsign"] == "W1AW":
            s["dx_country"] = "United States"
            s["dxcc"] = "291"
            s["source"] = "DX Summit"
        elif s["callsign"] == "VK3EPR":
            s["dx_country"] = "Australia"
            s["dxcc"] = "50"
            s["source"] = "DX Cluster"
        elif s["callsign"] == "ZS6DX":
            s["dx_country"] = "South Africa"
            s["dxcc"] = "197"
            s["source"] = "DX Summit"
        elif s["callsign"] == "JA1RAT":
            s["dx_country"] = "Japan"
            s["dxcc"] = "339"
            s["source"] = "DX Cluster"
    
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.route("**/qrz-cache", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": [["W1AW", "40M", "291"]], "last_modified": ""}),
    ))
    page.route("**/qrz-dxcc-numbers", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 2, "data": ["291", "50"], "last_modified": ""}),
    ))
    page.route("**/qrz-all-data", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": [["W1AW", "40M", "C"]], "last_modified": ""}),
    ))
    page.route("**/qrz-status", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"has_credentials": True, "callsign": "TEST"}),
    ))
    page.goto("http://localhost:8000")
    
    # Wait for data to load
    expect(page.get_by_text("Total Stations")).to_be_visible()
    
    # Enable Wanted filter
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    
    # Wait for the Wanted button to show it's enabled (mode 1)
    expect(page.get_by_role("button", name=re.compile("Wanted enabled"))).to_be_visible()
    
    # W1AW has DXCC 291 which IS in QRZ cache -> should NOT be highlighted
    w1aw_row = page.locator("tr").filter(has_text="W1AW").first
    classes = w1aw_row.get_attribute("class") or ""
    assert "bg-red-500/30" not in classes, f"W1AW (DXCC 291 in cache) should not be highlighted red, got: {classes}"
    
    # VK3EPR has DXCC 50 which IS in QRZ cache -> should NOT be highlighted
    vk_row = page.locator("tr").filter(has_text="VK3EPR").first
    vk_classes = vk_row.get_attribute("class") or ""
    assert "bg-red-500/30" not in vk_classes, f"VK3EPR (DXCC 50 in cache) should not be highlighted red, got: {vk_classes}"
    
    # ZS6DX has DXCC 197 which is NOT in QRZ cache -> should be highlighted with red
    zs_row = page.locator("tr").filter(has_text="ZS6DX").first
    zs_classes = zs_row.get_attribute("class") or ""
    assert "bg-red-500/30" in zs_classes, f"ZS6DX (DXCC 197 not in cache) should be highlighted red, got: {zs_classes}"
    
    # JA1RAT has DXCC 339 which is NOT in QRZ cache -> should be highlighted with red
    ja_row = page.locator("tr").filter(has_text="JA1RAT").first
    ja_classes = ja_row.get_attribute("class") or ""
    assert "bg-red-500/30" in ja_classes, f"JA1RAT (DXCC 339 not in cache) should be highlighted red, got: {ja_classes}"


def test_wanted_button_ignores_pota_stations(page: Page):
    """Wanted filter does not highlight POTA stations even when DXCC is not in cache."""
    mock = _mock_data(num_stations=3)
    for s in mock["stations"]:
        if s["source"] == "POTA":
            s["dx_country"] = "Palau"
            s["dxcc"] = "22"
        else:
            s["dxcc"] = ""
    
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.route("**/qrz-cache", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": [["W1AW", "40M", "291"]], "last_modified": ""}),
    ))
    page.route("**/qrz-dxcc-numbers", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": ["291"], "last_modified": ""}),
    ))
    page.route("**/qrz-all-data", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": [["W1AW", "40M", "C"]], "last_modified": ""}),
    ))
    page.route("**/qrz-status", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"has_credentials": True, "callsign": "TEST"}),
    ))
    page.goto("http://localhost:8000")
    
    expect(page.get_by_text("Total Stations")).to_be_visible()
    
    # Enable Wanted filter
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    
    # POTA station should NOT be highlighted
    pota_row = page.locator("tr").filter(has_text="P29V").first
    classes = pota_row.get_attribute("class") or ""
    assert "bg-red-500/30" not in classes, f"POTA station should not be highlighted, got: {classes}"


def test_wanted_button_normalizes_leading_zeros(page: Page):
    """Wanted filter correctly normalizes DXCC numbers with leading zeros."""
    mock = _mock_data(num_stations=3)
    for s in mock["stations"]:
        if s["callsign"] == "W1AW":
            s["dxcc"] = "0291"  # leading zero
        elif s["callsign"] == "VK3EPR":
            s["dxcc"] = "0050"  # leading zeros
        else:
            s["dxcc"] = ""
    
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.route("**/qrz-cache", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": [["W1AW", "40M", "291"]], "last_modified": ""}),
    ))
    page.route("**/qrz-dxcc-numbers", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": ["291"], "last_modified": ""}),
    ))
    page.route("**/qrz-all-data", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": [["W1AW", "40M", "C"]], "last_modified": ""}),
    ))
    page.route("**/qrz-status", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"has_credentials": True, "callsign": "TEST"}),
    ))
    page.goto("http://localhost:8000")
    
    expect(page.get_by_text("Total Stations")).to_be_visible()
    
    # Enable Wanted filter
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    
    # W1AW has DXCC 0291 which normalizes to 291 -> IS in cache -> should NOT be highlighted
    w1aw_row = page.locator("tr").filter(has_text="W1AW").first
    classes = w1aw_row.get_attribute("class") or ""
    assert "bg-red-500/30" not in classes, f"W1AW (DXCC 0291 normalized to 291 in cache) should not be highlighted, got: {classes}"
    
    # VK3EPR has DXCC 0050 which normalizes to 50 -> NOT in cache -> should be highlighted
    vk_row = page.locator("tr").filter(has_text="VK3EPR").first
    vk_classes = vk_row.get_attribute("class") or ""
    assert "bg-red-500/30" in vk_classes, f"VK3EPR (DXCC 0050 normalized to 50 not in cache) should be highlighted, got: {vk_classes}"


def test_wanted_row_color_is_red(page: Page):
    """Wanted rows use bg-red-500/30 class (not orange or other colors)."""
    mock = _mock_data(num_stations=3)
    for s in mock["stations"]:
        if s["callsign"] == "VK3EPR":
            s["dxcc"] = "50"
        else:
            s["dxcc"] = ""
    
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.route("**/qrz-cache", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": [["W1AW", "40M", "291"]], "last_modified": ""}),
    ))
    page.route("**/qrz-dxcc-numbers", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": ["291"], "last_modified": ""}),
    ))
    page.route("**/qrz-all-data", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": [["W1AW", "40M", "C"]], "last_modified": ""}),
    ))
    page.route("**/qrz-status", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"has_credentials": True, "callsign": "TEST"}),
    ))
    page.goto("http://localhost:8000")
    
    expect(page.get_by_text("Total Stations")).to_be_visible()
    
    # Enable Wanted filter
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    
    # VK3EPR should be highlighted with red, not orange
    vk_row = page.locator("tr").filter(has_text="VK3EPR").first
    vk_classes = vk_row.get_attribute("class") or ""
    assert "bg-red-500/30" in vk_classes, f"VK3EPR should have bg-red-500/30, got: {vk_classes}"
    assert "bg-orange" not in vk_classes, f"VK3EPR should NOT have orange class, got: {vk_classes}"


def test_only_wanted_shows_only_wanted_rows(page: Page):
    """Only wanted mode shows only stations with DXCC numbers not in QRZ cache."""
    mock = _mock_data(num_stations=5)
    for s in mock["stations"]:
        if s["callsign"] == "W1AW":
            s["dx_country"] = "United States"
            s["dxcc"] = "291"
            s["source"] = "DX Summit"
        elif s["callsign"] == "VK3EPR":
            s["dx_country"] = "Australia"
            s["dxcc"] = "50"
            s["source"] = "DX Cluster"
        elif s["callsign"] == "ZS6DX":
            s["dx_country"] = "South Africa"
            s["dxcc"] = "197"
            s["source"] = "DX Summit"
        elif s["callsign"] == "JA1RAT":
            s["dx_country"] = "Japan"
            s["dxcc"] = "339"
            s["source"] = "DX Cluster"
    
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.route("**/qrz-cache", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": [["W1AW", "40M", "291"]], "last_modified": ""}),
    ))
    page.route("**/qrz-dxcc-numbers", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 2, "data": ["291", "50"], "last_modified": ""}),
    ))
    page.route("**/qrz-all-data", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 1, "data": [["W1AW", "40M", "C"]], "last_modified": ""}),
    ))
    page.route("**/qrz-status", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"has_credentials": True, "callsign": "TEST"}),
    ))
    page.goto("http://localhost:8000")
    
    expect(page.get_by_text("Total Stations")).to_be_visible()
    
    # Click twice to reach "Only wanted" mode
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    expect(page.get_by_role("button", name=re.compile("Only wanted"))).to_be_visible()
    
    # Only ZS6DX and JA1RAT should be visible (DXCC 197 and 339 not in QRZ cache)
    zs_row = page.locator("tr").filter(has_text="ZS6DX").first
    expect(zs_row).to_be_visible()
    
    ja_row = page.locator("tr").filter(has_text="JA1RAT").first
    expect(ja_row).to_be_visible()
    
    # W1AW and VK3EPR should NOT be visible (DXCC 291 and 50 ARE in QRZ cache)
    w1aw_row = page.locator("tr").filter(has_text="W1AW").first
    expect(w1aw_row).not_to_be_visible()
    
    vk_row = page.locator("tr").filter(has_text="VK3EPR").first
    expect(vk_row).not_to_be_visible()


def test_wanted_button_color_changes(page: Page):
    """Wanted button color changes from emerald to red when enabled."""
    mock = _mock_data(num_stations=3)
    
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.route("**/qrz-status", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"has_credentials": True, "callsign": "TEST"}),
    ))
    page.route("**/qrz-cache", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"exists": True, "count": 0, "data": []}),
    ))
    page.route("**/qrz-dxcc-numbers", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"data": []}),
    ))
    page.route("**/qrz-all-data", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"data": []}),
    ))
    page.goto("http://localhost:8000")
    
    expect(page.get_by_text("Total Stations")).to_be_visible()
    
    # Initially emerald (disabled)
    button = page.get_by_role("button", name=re.compile("Wanted")).first
    classes = button.get_attribute("class") or ""
    assert "bg-emerald-600" in classes, f"Button should be emerald when disabled, got: {classes}"
    
    # Click to enable
    button.click()
    expect(page.get_by_role("button", name=re.compile("Wanted enabled"))).to_be_visible()
    
    # Now red (enabled)
    button = page.get_by_role("button", name=re.compile("Wanted enabled")).first
    classes = button.get_attribute("class") or ""
    assert "bg-red-600" in classes, f"Button should be red when enabled, got: {classes}"
    
    # Click to "Only wanted"
    button.click()
    expect(page.get_by_role("button", name=re.compile("Only wanted"))).to_be_visible()
    
    # Still red (only wanted)
    button = page.get_by_role("button", name=re.compile("Only wanted")).first
    classes = button.get_attribute("class") or ""
    assert "bg-red-600" in classes, f"Button should be red in only wanted mode, got: {classes}"
    
    # Click back to disabled
    button.click()
    expect(page.get_by_role("button", name=re.compile("Wanted disabled"))).to_be_visible()
    
    # Back to emerald
    button = page.get_by_role("button", name=re.compile("Wanted disabled")).first
    classes = button.get_attribute("class") or ""
    assert "bg-emerald-600" in classes, f"Button should be emerald when disabled, got: {classes}"


def test_wanted_icon_changes_with_mode(page: Page):
    """Wanted button icon changes: half-stroke -> star -> bullseye -> half-stroke."""
    mock = _mock_data(num_stations=3)
    
    page.route("**/data*", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(mock),
    ))
    page.route("**/qrz-status", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"has_credentials": True, "callsign": "TEST"}),
    ))
    page.goto("http://localhost:8000")
    
    expect(page.get_by_text("Total Stations")).to_be_visible()
    
    # Initially half-stroke icon (disabled)
    expect(page.locator("i.fas.fa-star-half-stroke")).to_be_visible()
    
    # Click to enable
    page.get_by_role("button", name=re.compile("Wanted")).first.click()
    expect(page.get_by_role("button", name=re.compile("Wanted enabled"))).to_be_visible()
    expect(page.locator("i.fas.fa-star")).to_be_visible()
    
    # Click to "Only wanted"
    page.get_by_role("button", name=re.compile("Wanted enabled")).first.click()
    expect(page.get_by_role("button", name=re.compile("Only wanted"))).to_be_visible()
    expect(page.locator("i.fas.fa-crosshairs")).to_be_visible()
    
    # Click back to disabled
    page.get_by_role("button", name=re.compile("Only wanted")).first.click()
    expect(page.get_by_role("button", name=re.compile("Wanted disabled"))).to_be_visible()
    expect(page.locator("i.fas.fa-star-half-stroke")).to_be_visible()
