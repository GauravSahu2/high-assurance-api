import pytest

# Mocking the Authentication Database
FAILED_ATTEMPTS_DB = {}

def mock_login_api(username, password):
    # Retrieve current failed attempts, default to 0
    attempts = FAILED_ATTEMPTS_DB.get(username, 0)
    
    # ATOMIC RULE: If attempts >= 5, the account is hard-locked.
    if attempts >= 5:
        return 423, "Account Locked due to suspicious activity."
        
    if password != "correct_password":
        FAILED_ATTEMPTS_DB[username] = attempts + 1
        return 401, "Invalid Credentials"
        
    # Reset on success
    FAILED_ATTEMPTS_DB[username] = 0
    return 200, "Login Success"

def test_account_lockout_mechanism():
    target_user = "admin_gaurav"
    
    # 1. Simulate 5 consecutive failed login attempts
    for _ in range(5):
        status, _ = mock_login_api(target_user, "wrong_guess")
        assert status == 401
        
    # 2. THE ASSERTION: The 6th attempt MUST return a 423 Locked status, even if the password is correct!
    status, msg = mock_login_api(target_user, "correct_password")
    
    assert status == 423, f"CRITICAL: Brute force protection failed! Status returned: {status}"
    print("\n[SUCCESS] Auth Rate Limiting verified. Account successfully locked after 5 failed attempts.")
