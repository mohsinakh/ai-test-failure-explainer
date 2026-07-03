
---
# Run started 2026-07-03T13:13:08.568237

## tests/demo_failures/test_demo_failures.py::test_ui_failure_demo_error_banner_after_valid_login[chromium]
_2026-07-03T13:14:25.793741_

ROOT CAUSE: The error banner with the data-test="error" locator is not visible on the page, indicating that an error has occurred but it's not being displayed to the user.
LIKELY CATEGORY: Product Bug
SUGGESTED FIX: Check the application code for any recent changes related to error handling and display, specifically looking at how the error banner is generated and displayed.

---

## tests/demo_failures/test_demo_failures.py::test_api_failure_demo_wrong_token_field_name
_2026-07-03T13:15:01.990325_

ROOT CAUSE: The test is expecting the token field to be named 'token' but it's actually named 'accessToken'.
LIKELY CATEGORY: Product Bug
SUGGESTED FIX: Update the test code to match the actual field name in the API response.

---
