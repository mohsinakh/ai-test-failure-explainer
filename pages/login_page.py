"""
Page Object for the SauceDemo login page.

We're testing against https://www.saucedemo.com as a stand-in for TestMu's
own Login module, since no staging URL was provided in the ticket. See
README.md "About the target application" for the full rationale.
"""


class LoginPage:
    URL = "https://www.saucedemo.com/"

    def __init__(self, page):
        self.page = page
        self.username_input = page.locator("#user-name")
        self.password_input = page.locator("#password")
        self.login_button = page.locator("#login-button")
        self.error_message = page.locator('[data-test="error"]')

    def goto(self):
        self.page.goto(self.URL)
        return self

    def login(self, username: str, password: str):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()
        return self

    def logout(self):
        self.page.locator("#react-burger-menu-btn").click()
        self.page.locator("#logout_sidebar_link").click()
        return self

    def get_error_text(self) -> str:
        return self.error_message.inner_text()
