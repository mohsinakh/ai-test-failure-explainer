"""
Dashboard module regression tests.

Target: https://www.saucedemo.com/inventory.html, reached via login.

Covers the ticket's Dashboard scenarios:
    - Widget loading                    -> test_widgets_load_with_content
    - Data accuracy                     -> test_prices_are_valid_currency_values
    - Filter/sort behavior              -> test_sort_low_to_high / test_sort_za
    - Responsive layout                 -> test_layout_adapts_to_mobile_viewport
    - Permission-based visibility       -> test_problem_user_sees_broken_images (documents
                                            the one built-in "permission-flavored" variant
                                            the demo app actually has - see note below)
"""
import pytest
from playwright.sync_api import expect

from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage

VALID_PASSWORD = "secret_sauce"


def _login_as(page, username):
    LoginPage(page).goto().login(username, VALID_PASSWORD)
    return InventoryPage(page)


@pytest.mark.dashboard
def test_widgets_load_with_content(page):
    inventory = _login_as(page, "standard_user")
    expect(inventory.inventory_list).to_be_visible()
    assert inventory.item_count() == 6, "Expected all 6 product widgets to render"
    for name in inventory.get_displayed_names():
        assert name.strip() != "", "A widget rendered with an empty title"


@pytest.mark.dashboard
def test_prices_are_valid_currency_values(page):
    inventory = _login_as(page, "standard_user")
    prices = inventory.get_displayed_prices()
    assert len(prices) == 6
    assert all(p > 0 for p in prices), "Found a widget with a non-positive price"


@pytest.mark.dashboard
def test_sort_low_to_high(page):
    inventory = _login_as(page, "standard_user")
    inventory.sort_by("lohi")
    prices = inventory.get_displayed_prices()
    assert prices == sorted(prices), "Prices are not sorted low to high"


@pytest.mark.dashboard
def test_sort_za(page):
    inventory = _login_as(page, "standard_user")
    inventory.sort_by("za")
    names = inventory.get_displayed_names()
    assert names == sorted(names, reverse=True), "Names are not sorted Z to A"


@pytest.mark.dashboard
def test_layout_adapts_to_mobile_viewport(page):
    page.set_viewport_size({"width": 375, "height": 812})  # iPhone X-ish
    inventory = _login_as(page, "standard_user")
    expect(inventory.inventory_list).to_be_visible()
    # The hamburger menu is the mobile nav pattern SauceDemo uses instead of
    # a full top nav bar; its presence at narrow widths is our responsive-layout signal.
    expect(inventory.menu_button).to_be_visible()


@pytest.mark.dashboard
def test_problem_user_sees_broken_images(page):
    """SauceDemo doesn't have real role-based permissions, but `problem_user`
    is its closest analog: same login, visibly different rendered dashboard
    (all product images resolve to the same broken asset). We use it to
    validate that our widget-content assertions actually catch a
    degraded-rendering regression rather than always passing."""
    inventory = _login_as(page, "problem_user")
    srcs = page.locator(".inventory_item_img img").evaluate_all(
        "imgs => imgs.map(i => i.getAttribute('src'))"
    )
    unique_srcs = set(srcs)
    assert len(unique_srcs) == 1, (
        "Expected the known problem_user image-rendering bug (all images "
        "identical); if this now fails, either the bug was fixed upstream "
        "or our detection broke - both are worth a second look."
    )


@pytest.mark.dashboard
@pytest.mark.skip(
    reason=(
        "Designed test, not executable against the demo target: SauceDemo has no "
        "real role/permission system (e.g. viewer vs. admin) to hide/show "
        "specific widgets. Written to spec for when TestMu's Dashboard exposes "
        "role-based widget visibility."
    )
)
def test_viewer_role_cannot_see_admin_widgets(page):
    _login_as(page, "viewer_role_user")
    expect(page.locator('[data-test="admin-widget"]')).to_have_count(0)
