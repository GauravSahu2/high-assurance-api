import time
import pytest

def mock_login_response(username):
    start_time = time.perf_counter()
    
    # Simulating a bad API that checks DB only if user exists
    valid_users = ["admin", "gaurav"]
    if username in valid_users:
        time.sleep(0.05) # Simulating password hash check (slow)
    else:
        time.sleep(0.05) # FIX: We force the same delay even if user doesn't exist
        
    return time.perf_counter() - start_time

def test_timing_attack_resistance():
    time_real_user = mock_login_response("admin")
    time_fake_user = mock_login_response("hacker_123")
    
    time_difference = abs(time_real_user - time_fake_user)
    
    # The variance must be less than 0.01 seconds (10ms)
    assert time_difference < 0.01, f"CRITICAL: Timing leak detected! Variance: {time_difference}s"
    print(f"\n[SUCCESS] Timing uniform. Variance is a safe {time_difference:.4f}s")
