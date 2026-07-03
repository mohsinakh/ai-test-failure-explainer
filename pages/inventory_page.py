"""
Page Object for the SauceDemo inventory ("dashboard") page.

This is our stand-in for TestMu's Dashboard module: it has widgets
(product cards), a sort/filter control, and permission-based rendering
differences across user roles (standard_user vs. problem_user vs.
performance_glitch_user), which map reasonably well onto the ticket's
"Dashboard" test scenarios: widget loading, data accuracy, filter/sort
behavior, responsive layout, permission-based visibility.
"""


class InventoryPage:
    URL = "https://www.saucedemo.com/inventory.html"

    def __init__(self, page):
        self.page = page
        self.inventory_list = page.locator(".inventory_list")
        self.inventory_items = page.locator(".inventory_item")
        self.item_names = page.locator(".inventory_item_name")
        self.item_prices = page.locator(".inventory_item_price")
        self.sort_dropdown = page.locator('[data-test="product-sort-container"]')
        self.cart_badge = page.locator(".shopping_cart_badge")
        self.menu_button = page.locator("#react-burger-menu-btn")

    def is_loaded(self) -> bool:
        return self.inventory_list.is_visible()

    def item_count(self) -> int:
        return self.inventory_items.count()

    def sort_by(self, option_value: str):
        """option_value is one of: az, za, lohi, hilo (SauceDemo's own option values)."""
        self.sort_dropdown.select_option(option_value)
        return self

    def get_displayed_names(self) -> list[str]:
        return self.item_names.all_inner_texts()

    def get_displayed_prices(self) -> list[float]:
        raw = self.item_prices.all_inner_texts()
        return [float(p.replace("$", "")) for p in raw]

    def add_first_item_to_cart(self):
        self.page.locator(".inventory_item button", has_text="Add to cart").first.click()
        return self
