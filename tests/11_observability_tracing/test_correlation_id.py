from main import app as flask_app


def test_correlation_id_injected_into_response():
    """Verifies the middleware injects X-Correlation-ID into every response."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        res = c.get("/health")
    assert res.status_code == 200
    assert "X-Correlation-ID" in res.headers


def test_correlation_id_echoes_request_header():
    """Verifies the middleware echoes back a provided X-Correlation-ID."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        res = c.get("/health", headers={"X-Correlation-ID": "test-trace-abc"})
    assert res.headers.get("X-Correlation-ID") == "test-trace-abc"
