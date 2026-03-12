import pytest

def mock_api_request(user_token, target_account_id):
    # Simulated API logic: Token A belongs to Account 100
    token_database = {"Token_A": "100", "Token_B": "200"}
    
    if user_token not in token_database:
        return 401 # Unauthorized
    
    if token_database[user_token] != target_account_id:
        return 403 # Forbidden (BOLA Blocked)
        
    return 200 # OK

def test_bola_prevention():
    # User A tries to access User A's data (Should Pass)
    assert mock_api_request("Token_A", "100") == 200
    
    # SPY-GRADE: User A tries to access User B's data (Must be Blocked)
    assert mock_api_request("Token_A", "200") == 403
    
    print("\n[SUCCESS] BOLA vulnerability mitigated: User boundaries enforced.")
