import requests

def test_correlation_id_injected_into_response():
    """Verifies the live API middleware actively injects tracing headers."""
    res = requests.get("http://127.0.0.1:8000/health")
    
    assert res.status_code == 200
    assert "X-Correlation-ID" in res.headers, "API middleware failed to inject trace ID"
    assert len(res.headers["X-Correlation-ID"]) > 10 # Verifies it's a generated UUID
