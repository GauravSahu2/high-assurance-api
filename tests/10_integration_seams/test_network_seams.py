import requests

TARGET_URL = "http://127.0.0.1:8000/health"

def test_cors_rejects_malicious_origin():
    """
    Verifies the API does not blindly echo back malicious CORS origins.
    """
    headers = {"Origin": "https://evil-hacker-site.com"}
    response = requests.options(TARGET_URL, headers=headers)
    
    allowed_origin = response.headers.get('Access-Control-Allow-Origin')
    # Assert that the API explicitly denied the evil site
    assert allowed_origin != 'https://evil-hacker-site.com'
