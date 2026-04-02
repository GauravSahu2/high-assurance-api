import os

from main import app as flask_app


def test_health_endpoint_triggers_rollback_flag_on_degradation():
    """Verifies that a degraded API correctly signals load balancers to roll back traffic."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        # Inject Chaos to simulate a bad deployment
        os.environ["CHAOS_MODE"] = "true"
        from unittest.mock import patch

        with patch("random.random", return_value=0.0):  # Force the 503
            res = c.get("/health")

        assert res.status_code == 503
        assert res.get_json()["status"] == "chaos"
        del os.environ["CHAOS_MODE"]
