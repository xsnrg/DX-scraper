from playwright.sync_api import Page, expect

from conftest import _mock_data, open_dashboard, qrz_ready_kwargs


def test_setup_qrz_button_visible_without_credentials(page: Page):
    """With no stored credentials the dashboard offers Setup QRZ."""
    open_dashboard(page)
    expect(page.get_by_role("button", name="Setup QRZ")).to_be_visible()


def test_qrz_filter_button_visible(page: Page):
    """QRZ filter button is visible on the dashboard."""
    open_dashboard(page)
    expect(page.get_by_role("button", name="QRZ filter disabled")).to_be_visible()


def test_qrz_setup_opens_modal(page: Page):
    """Clicking Setup QRZ opens the credentials modal."""
    open_dashboard(page)
    page.get_by_role("button", name="Setup QRZ").click()
    expect(page.get_by_text("QRZ.com API Credentials")).to_be_visible()


def test_qrz_modal_has_callsign_and_token_fields(page: Page):
    """QRZ modal contains callsign and API token inputs."""
    open_dashboard(page)
    page.get_by_role("button", name="Setup QRZ").click()
    expect(page.get_by_placeholder("AB1CD")).to_be_visible()
    expect(page.get_by_placeholder("Enter your QRZ.com API token")).to_be_visible()
    expect(page.get_by_role("button", name="Save")).to_be_visible()


def test_qrz_modal_cancel_closes_it(page: Page):
    """Cancel dismisses the QRZ credentials modal."""
    open_dashboard(page)
    page.get_by_role("button", name="Setup QRZ").click()
    expect(page.get_by_text("QRZ.com API Credentials")).to_be_visible()
    page.get_by_role("button", name="Cancel").click()
    expect(page.get_by_text("QRZ.com API Credentials")).not_to_be_visible()


def test_qrz_modal_outside_click_closes(page: Page):
    """Clicking the overlay (outside the dialog) closes the QRZ modal."""
    open_dashboard(page)
    page.get_by_role("button", name="Setup QRZ").click()
    expect(page.get_by_text("QRZ.com API Credentials")).to_be_visible()
    page.locator(".fixed.inset-0").click(position={"x": 4, "y": 4})
    expect(page.get_by_text("QRZ.com API Credentials")).not_to_be_visible()


def test_qrz_refresh_button_when_credentials_exist(page: Page):
    """Stored credentials change the QRZ button to Refresh QRZ Data."""
    open_dashboard(page, **qrz_ready_kwargs())
    expect(page.get_by_role("button", name="Refresh QRZ Data")).to_be_visible()


def test_qrz_filter_hides_confirmed_contacts(page: Page):
    """Enabling QRZ filter hides stations already confirmed on that band."""
    mock = _mock_data(num_stations=3)
    open_dashboard(page, mock, **qrz_ready_kwargs(
        cache_data=[["W1AW", "40M", "291"]],
        dxcc_numbers=["291"],
    ))
    expect(page.get_by_role("cell", name="W1AW")).to_be_visible()
    expect(page.get_by_role("cell", name="VK3EPR")).to_be_visible()

    page.get_by_role("button", name="QRZ filter disabled").click()
    expect(page.get_by_role("button", name="QRZ filter enabled")).to_be_visible()
    expect(page.get_by_role("cell", name="W1AW")).not_to_be_visible()
    expect(page.get_by_role("cell", name="VK3EPR")).to_be_visible()
