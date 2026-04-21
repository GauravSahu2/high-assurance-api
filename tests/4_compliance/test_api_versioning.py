"""
Compliance Test: API Versioning & Deprecation Awareness
═══════════════════════════════════════════════════════════
Frameworks: SOC 2 CC8.1, NIST PM-30, API Design Best Practices

Validates:
  • API has a discoverable specification (OpenAPI)
  • Response structure is consistent across endpoints
  • Breaking changes are detectable via contract testing
  • API root provides service metadata
"""


class TestAPIContractStability:
    """SOC 2 CC8.1: Changes must be managed and communicated."""

    def test_root_endpoint_returns_service_info(self, client):
        """API root must identify the service."""
        res = client.get("/")
        assert res.status_code == 200
        data = res.get_json()
        assert "message" in data, "Root endpoint must return a message"

    def test_openapi_spec_accessible(self, client):
        """SOC 2: API contract must be publicly documented."""
        res = client.get("/openapi.yaml")
        assert res.status_code == 200
        body = res.get_data(as_text=True)
        assert len(body) > 100, "OpenAPI spec must have meaningful content"

    def test_all_error_responses_have_consistent_shape(self, client):
        """API Design: All errors must use the same response shape."""
        # Collect various error responses
        errors = [
            client.get("/nonexistent"),  # 404
            client.post("/transfer", json={}),  # 401
            client.post("/login", json={"username": 123, "password": 456}),  # 400
        ]
        for res in errors:
            data = res.get_json()
            assert data is not None, f"HTTP {res.status_code} must return JSON"
            assert "error" in data, f"HTTP {res.status_code} response missing 'error' key: {data}"

    def test_success_responses_have_consistent_shape(self, client):
        """API Design: Success responses must follow a predictable structure."""
        # Health check
        res = client.get("/health")
        data = res.get_json()
        assert "status" in data, "Health response must include 'status'"

        # Login
        res = client.post("/login", json={"username": "admin", "password": "password123"})
        data = res.get_json()
        assert "token" in data, "Login response must include 'token'"

    def test_login_response_follows_oauth2_spec(self, client):
        """RFC 6749: Login response should follow OAuth 2.0 token response format."""
        res = client.post("/login", json={"username": "admin", "password": "password123"})
        data = res.get_json()
        # OAuth 2.0 standard fields
        assert "access_token" in data, "Missing OAuth 2.0 'access_token' field"
        assert "token_type" in data, "Missing OAuth 2.0 'token_type' field"
        assert data["token_type"] == "bearer", "token_type must be 'bearer'"
        assert "expires_in" in data, "Missing OAuth 2.0 'expires_in' field"
        assert isinstance(data["expires_in"], int), "expires_in must be integer"

    def test_content_type_is_json_for_api_responses(self, client):
        """API Design: All API responses must declare Content-Type."""
        endpoints = [("/", "GET"), ("/health", "GET")]
        for path, method in endpoints:
            res = client.open(path, method=method)
            ct = res.headers.get("Content-Type", "")
            assert "application/json" in ct, f"{method} {path} missing JSON content type (got: {ct})"

    def test_unknown_fields_in_request_body_ignored(self, client):
        """Robustness: Extra fields in requests should not cause errors."""
        res = client.post(
            "/login",
            json={
                "username": "admin",
                "password": "password123",
                "extra_field": "should_be_ignored",
                "version": "v99",
            },
        )
        assert res.status_code == 200, "Extra fields in request should be safely ignored"
