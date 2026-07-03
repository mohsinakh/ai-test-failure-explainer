"""
Deliberately failing tests - kept separate from the real regression suite
on purpose.

Why these exist: a healthy suite gives the Failure Explainer (Task 3)
nothing to actually analyze. These two tests make real calls against the
real targets (SauceDemo, DummyJSON) - nothing here is mocked - but assert
something intentionally wrong, so there's a genuine failure for the
explainer to reason about end to end. Neither represents an actual bug in
SauceDemo or DummyJSON.

They're tagged `demo_failure` (registered in pytest.ini) specifically so
they're easy to tell apart from real regression results:

    # Run everything, including these (what a plain `pytest` already does):
    pytest --html=reports/report.html --self-contained-html

    # Run ONLY the demo failures, to check the explainer in isolation:
    pytest -m demo_failure --html=reports/report.html --self-contained-html

    # Run the real suite WITHOUT these, once you've seen the explainer work:
    pytest -m "not demo_failure" --html=reports/report.html --self-contained-html
"""
import requests
import pytest
from playwright.sync_api import expect

from pages.login_page import LoginPage

BASE_URL = "https://dummyjson.com"


@pytest.mark.demo_failure
def test_ui_failure_demo_error_banner_after_valid_login(page):
    """Logs in with VALID credentials - then asserts the error banner
    should be visible, which it never is after a successful login. This
    gives the explainer a real Playwright TimeoutError with a real page
    URL and real visible page text to reason about, so you can see it
    correctly identify 'app worked fine, assertion is just wrong' as a
    Test Script Issue rather than a Product Bug."""
    login_page = LoginPage(page).goto()
    login_page.login("standard_user", "secret_sauce")

    expect(login_page.error_message).to_be_visible(timeout=5000)  # intentionally wrong


@pytest.mark.demo_failure
def test_api_failure_demo_wrong_token_field_name(api_context):
    """Real login call against DummyJSON, real 200 response - then an
    intentionally wrong field-name assertion (DummyJSON's field is
    'accessToken', this checks for 'token'). This is the exact scenario
    written up by hand in llm_integration/sample_output.md, now runnable
    for real: same root cause (schema mismatch between what the test
    expects and what the API actually returns), live API response
    attached for the explainer to read."""
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "emilys", "password": "emilyspass"},
    )
    body = resp.json()
    api_context["response"] = {
        "status_code": resp.status_code,
        "url": resp.url,
        "body": body,
    }

    assert "token" in body  # intentionally wrong - real field name is "accessToken"