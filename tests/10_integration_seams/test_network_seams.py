from main import app as flask_app


def test_cors_rejects_malicious_origin():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        response = c.options("/health", headers={"Origin": "https://evil-hacker-site.com"})
    assert response.headers.get("Access-Control-Allow-Origin") != "https://evil-hacker-site.com"
