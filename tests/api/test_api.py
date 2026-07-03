"""
REST API module regression tests.

Target: https://dummyjson.com - a free, no-signup fake REST API with a real
auth/login endpoint (returns a real JWT), simulated CRUD (writes echo back a
plausible response but don't persist - documented where it matters), and
real 4xx error responses. Chosen over reqres.in, which as of this writing
requires a signed-up x-api-key for most endpoints (a mismatch for a
"hit it and go" regression suite), and whose own blog now markets a
signup flow specifically at AI coding agents - not something we want this
suite quietly depending on.

Covers the ticket's REST API scenarios:
    - Auth token validation      -> TestAuth
    - CRUD operations            -> TestProductCRUD
    - Error handling (4xx/5xx)   -> TestErrorHandling
    - Rate limiting              -> TestRateLimiting (documented limitation, see class docstring)
    - Schema validation          -> TestSchemaValidation
"""
import requests
import pytest

BASE_URL = "https://dummyjson.com"
VALID_USERNAME = "emilys"
VALID_PASSWORD = "emilyspass"


@pytest.mark.api
class TestAuth:
    def test_login_with_valid_credentials_returns_token(self, api_context):
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": VALID_USERNAME, "password": VALID_PASSWORD},
        )
        api_context["response"] = _summarize(resp)

        assert resp.status_code == 200
        body = resp.json()
        assert "accessToken" in body and len(body["accessToken"]) > 20
        assert body["username"] == VALID_USERNAME

    def test_login_with_invalid_password_is_rejected(self, api_context):
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": VALID_USERNAME, "password": "definitely_wrong"},
        )
        api_context["response"] = _summarize(resp)

        assert resp.status_code in (400, 401)

    def test_protected_endpoint_requires_token(self, api_context):
        resp = requests.get(f"{BASE_URL}/auth/me")
        api_context["response"] = _summarize(resp)
        assert resp.status_code == 401

    def test_protected_endpoint_accepts_valid_token(self, api_context):
        login = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": VALID_USERNAME, "password": VALID_PASSWORD},
        )
        token = login.json()["accessToken"]

        resp = requests.get(
            f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        api_context["response"] = _summarize(resp)

        assert resp.status_code == 200
        assert resp.json()["username"] == VALID_USERNAME


@pytest.mark.api
class TestProductCRUD:
    """DummyJSON's writes are simulated: the API returns a well-formed,
    plausible response (correct id, echoed fields) but does not persist
    the change server-side. We assert on the response contract, which is
    what a regression suite against a fake backend can meaningfully check;
    the README flags this as a known gap versus a real staging DB."""

    def test_create_product(self, api_context):
        resp = requests.post(
            f"{BASE_URL}/products/add",
            json={"title": "Regression Test Widget", "price": 19.99},
        )
        api_context["response"] = _summarize(resp)

        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Regression Test Widget"
        assert "id" in body

    def test_read_single_product(self, api_context):
        resp = requests.get(f"{BASE_URL}/products/1")
        api_context["response"] = _summarize(resp)

        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    def test_update_product(self, api_context):
        resp = requests.put(f"{BASE_URL}/products/1", json={"title": "Updated Title"})
        api_context["response"] = _summarize(resp)

        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_delete_product(self, api_context):
        resp = requests.delete(f"{BASE_URL}/products/1")
        api_context["response"] = _summarize(resp)

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("isDeleted") is True


@pytest.mark.api
class TestErrorHandling:
    def test_get_nonexistent_product_returns_404(self, api_context):
        resp = requests.get(f"{BASE_URL}/products/999999")
        api_context["response"] = _summarize(resp)
        assert resp.status_code == 404

    def test_malformed_login_body_returns_4xx(self, api_context):
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            data="not-json",
            headers={"Content-Type": "application/json"},
        )
        api_context["response"] = _summarize(resp)
        assert 400 <= resp.status_code < 500

    def test_missing_required_field_on_login_returns_4xx(self, api_context):
        resp = requests.post(f"{BASE_URL}/auth/login", json={"username": VALID_USERNAME})
        api_context["response"] = _summarize(resp)
        assert 400 <= resp.status_code < 500


@pytest.mark.api
class TestSchemaValidation:
    REQUIRED_PRODUCT_FIELDS = {"id", "title", "price", "description", "category", "stock"}

    def test_product_list_items_match_expected_schema(self, api_context):
        resp = requests.get(f"{BASE_URL}/products?limit=5")
        api_context["response"] = _summarize(resp)

        body = resp.json()
        assert "products" in body
        for product in body["products"]:
            missing = self.REQUIRED_PRODUCT_FIELDS - product.keys()
            assert not missing, f"Product {product.get('id')} missing fields: {missing}"
            assert isinstance(product["price"], (int, float))
            assert isinstance(product["title"], str) and product["title"] != ""

    def test_login_response_matches_expected_schema(self, api_context):
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": VALID_USERNAME, "password": VALID_PASSWORD},
        )
        api_context["response"] = _summarize(resp)

        body = resp.json()
        for field in ("id", "username", "email", "accessToken", "refreshToken"):
            assert field in body, f"Login response missing '{field}'"


@pytest.mark.api
class TestRateLimiting:
    """DummyJSON does not document or enforce a hard rate limit, so we can't
    meaningfully assert a 429 shows up at a known threshold - that would be
    testing DummyJSON's infrastructure, not TestMu's. What we *can* assert
    is the property that matters for a real regression suite: a burst of
    requests fails safely (no client-side crash, every response is either
    a valid 2xx or a well-formed error) rather than hanging or corrupting
    state. This is the honest version of this test against a demo target;
    against TestMu's real API it should be tightened to assert an actual
    429 + Retry-After once the endpoint enforces one."""

    def test_burst_of_requests_completes_without_crashing(self, api_context):
        statuses = []
        for _ in range(15):
            resp = requests.get(f"{BASE_URL}/products/1")
            statuses.append(resp.status_code)

        api_context["response"] = {"statuses": statuses}
        assert all(s == 200 or s == 429 for s in statuses)
        if 429 in statuses:
            assert statuses.count(429) < len(statuses), "Every request was rate-limited"


def _summarize(resp: requests.Response) -> dict:
    """Small, LLM-friendly snapshot of an HTTP response for failure analysis."""
    try:
        body = resp.json()
    except ValueError:
        body = resp.text[:500]
    return {
        "status_code": resp.status_code,
        "url": resp.url,
        "body": body,
    }
