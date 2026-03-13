import requests

def test_ip_based_brute_force_lockout():
    """Hits the live API to verify IP-based rate limiting engages after 5 failures."""
    url = "http://127.0.0.1:8000/login"
    payload = {"username": "admin", "password": "wrongpassword"}
    
    # Send 5 unauthorized attempts
    for _ in range(5):
        res = requests.post(url, json=payload)
        assert res.status_code == 401
        
    # The 6th attempt must trigger the 429 Too Many Requests IP Lockout
    res = requests.post(url, json=payload)
    assert res.status_code == 429
    assert "Account locked" in res.json().get("error", "")
