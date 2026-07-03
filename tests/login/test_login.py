"""
Login module regression tests.

Target: https://www.saucedemo.com (see README for why).

Covers the ticket's Login scenarios:
    - Valid login                      -> test_valid_login_redirects_to_inventory
    - Invalid credentials               -> test_invalid_credentials_shows_error
    - Forgot password                   -> test_forgot_password_flow (SKIPPED, see reason)
    - Session expiry                    -> test_logout_ends_session
    - Brute-force lockout               -> test_locked_out_account_is_rejected

SauceDemo doesn't implement a self-serve "forgot password" flow or a
dynamic brute-force lockout counter (it ships one hardcoded
`locked_out_user` instead). Rather than fake those against a site that
doesn't have them, we've written the test to spec and marked it
`skip` with a clear reason, the way we would against a real staging
app that hadn't shipped the feature yet. That test still documents the
exact assertion we'd run the day the feature lands.
"""
import re
import pytest
from playwright.sync_api import expect

from pages.login_page import LoginPage

VALID_USER = "standard_user"
VALID_PASSWORD = "secret_sauce"


@pytest.mark.login
def test_valid_login_redirects_to_inventory(page):
    login_page = LoginPage(page).goto()
    login_page.login(VALID_USER, VALID_PASSWORD)

    expect(page).to_have_url(re.compile(r".*inventory\.html"))
    expect(page.locator(".inventory_list")).to_be_visible()


@pytest.mark.login
@pytest.mark.parametrize(
    "username,password,test_id",
    [
        ("standard_user", "wrong_password", "wrong-password"),
        ("not_a_real_user", "secret_sauce", "wrong-username"),
        ("", "secret_sauce", "blank-username"),
        ("standard_user", "", "blank-password"),
        ("", "", "blank-both"),
    ],
)
def test_invalid_credentials_shows_error(page, username, password, test_id):
    login_page = LoginPage(page).goto()
    login_page.login(username, password)

    expect(login_page.error_message).to_be_visible()
    expect(page).to_have_url(LoginPage.URL)  # never leaves the login page


@pytest.mark.login
def test_locked_out_account_is_rejected(page):
    """Stand-in for brute-force lockout: SauceDemo ships a permanently
    locked account rather than a live attempt counter. This test verifies
    the *lockout enforcement* behavior (blocked + clear message), which is
    the part of "brute-force lockout" that's actually testable here."""
    login_page = LoginPage(page).goto()
    login_page.login("locked_out_user", VALID_PASSWORD)

    expect(login_page.error_message).to_contain_text("locked out")
    expect(page).to_have_url(LoginPage.URL)


@pytest.mark.login
def test_logout_ends_session(page):
    """Proxy for "session expiry": after logout, the session must be
    considered invalid, so navigating straight to a protected URL should
    bounce back to login rather than render the inventory page."""
    login_page = LoginPage(page).goto()
    login_page.login(VALID_USER, VALID_PASSWORD)
    expect(page).to_have_url(re.compile(r".*inventory\.html"))

    login_page.logout()
    expect(page).to_have_url(LoginPage.URL)

    # Attempt to re-enter a protected page directly with no active session.
    page.goto("https://www.saucedemo.com/inventory.html")
    expect(page).to_have_url(re.compile(r".*/$|.*index\.html"))
    expect(login_page.error_message).to_be_visible()


@pytest.mark.login
@pytest.mark.skip(
    reason=(
        "Designed test, not executable against the demo target: SauceDemo has no "
        "'forgot password' flow. Kept here (instead of deleted) so the assertion "
        "is ready to enable the day TestMu's real Login module ships this feature. "
        "See prompts.md -> Login module notes for the prompt iteration that "
        "surfaced this gap."
    )
)
def test_forgot_password_flow(page):
    page.goto(LoginPage.URL)
    page.locator("text=Forgot your password?").click()
    page.locator("#email").fill("user@example.com")
    page.locator("#reset-submit").click()
    expect(page.locator(".reset-confirmation")).to_contain_text(
        "check your email for a reset link"
    )
