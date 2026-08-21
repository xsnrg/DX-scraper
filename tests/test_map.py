from playwright.sync_api import Page, expect

from conftest import DASHBOARD_URL, open_dashboard


def test_map_link_visible_on_dashboard(page: Page):
    """Map link button is visible on the dashboard."""
    open_dashboard(page)
    expect(page.get_by_role("link", name="Map my QSOs")).to_be_visible()


def test_map_link_navigates_to_map(page: Page):
    """Clicking Map link navigates to the DXCC map page."""
    open_dashboard(page)
    page.get_by_role("link", name="Map my QSOs").click()
    expect(page).to_have_url(f"{DASHBOARD_URL}/dxcc-map.html")


def test_map_page_has_title(page: Page):
    """DXCC map page has the correct title."""
    page.goto(f"{DASHBOARD_URL}/dxcc-map.html")
    expect(page).to_have_title("DXCC QSL Status Map")


def test_map_page_has_map_element(page: Page):
    """DXCC map page has a map container element."""
    page.goto(f"{DASHBOARD_URL}/dxcc-map.html")
    expect(page.get_by_role("img")).to_be_visible()


def test_map_page_has_country_list(page: Page):
    """DXCC map page has a country list sidebar."""
    page.goto(f"{DASHBOARD_URL}/dxcc-map.html")
    expect(page.get_by_text("DXCC Countries")).to_be_visible()


def test_map_page_has_search_box(page: Page):
    """DXCC map page has a search input for countries."""
    page.goto(f"{DASHBOARD_URL}/dxcc-map.html")
    expect(page.get_by_placeholder("Search countries...")).to_be_visible()


def test_map_page_has_legend(page: Page):
    page.goto(f"{DASHBOARD_URL}/dxcc-map.html")
    expect(page.get_by_text("Confirmed (2-way QSL)")).to_be_visible()
    expect(page.get_by_text("Logged (not verified)")).to_be_visible()
    expect(page.get_by_text("Not in cache", exact=True)).to_be_visible()


def test_hawaii_has_dxcc_110(page: Page):
    """Hawaii is DXCC 110 in the countries data."""
    response = page.request.get(f"{DASHBOARD_URL}/static/dxcc-countries.js")
    assert response.status == 200
    lines = response.text().split("\n")
    hawaii_line = [line for line in lines if '"Hawaii"' in line]
    assert len(hawaii_line) == 1, "Hawaii entry not found"
    assert 'dxcc: "110"' in hawaii_line[0], f"Hawaii should be DXCC 110, got: {hawaii_line[0]}"


def test_dxcc_map_html_uses_dxcc_key(page: Page):
    """DXCC map HTML uses DXCC numbers for qslData lookup, not country names."""
    response = page.request.get(f"{DASHBOARD_URL}/dxcc-map.html")
    assert response.status == 200
    html = response.text()
    assert "qslData[country.dxcc]" in html, "Map should use DXCC numbers for qslData lookup"
    assert "qslData[country.name]" not in html, "Map should not use country names for qslData lookup"
    assert "getCountryColor(country)" in html, "getCountryColor should receive country object"
    assert "getCountryColor(country.name)" not in html, "getCountryColor should not receive just country name"


def test_qrz_filter_uses_station_band_not_bands(page: Page):
    """Frontend uses station.band (singular) not station.bands (plural) for QRZ filtering."""
    response = page.request.get(f"{DASHBOARD_URL}/")
    assert response.status == 200
    html = response.text()
    assert "station.band" in html, "Frontend should use station.band (singular) to match DXStation model"
    assert "station.bands" not in html, "Frontend should not use station.bands (plural)"
    assert "s.band" in html, "Filtering logic should use s.band (singular)"
    assert "s.bands" not in html, "Filtering logic should not use s.bands (plural)"


def test_map_back_to_dashboard(page: Page):
    """Map page has a link back to the dashboard."""
    page.goto(f"{DASHBOARD_URL}/dxcc-map.html")
    expect(page.get_by_role("link", name="DX Monitor")).to_be_visible()
