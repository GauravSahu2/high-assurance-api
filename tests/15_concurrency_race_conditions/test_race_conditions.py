import threading
import concurrent.futures
import time
import pytest

# Simulated Shared Database State
DATABASE = {"account_123_balance": 100}

# The Architectural Fix: A Mutex (Mutual Exclusion) Lock
# In a real DB, this represents Row-Level Locking (e.g., SELECT ... FOR UPDATE)
db_lock = threading.Lock()

def withdraw_funds(amount):
    global DATABASE
    
    # The thread attempts to acquire the lock before reading or writing
    with db_lock:
        current_balance = DATABASE["account_123_balance"]
        
        # Check if enough funds exist
        if current_balance >= amount:
            # Simulate network/database processing delay (this is where race conditions happen!)
            time.sleep(0.05) 
            
            # Deduct the funds
            DATABASE["account_123_balance"] -= amount
            return True # Transaction Success
            
        return False # Transaction Failed (Insufficient Funds)

def test_prevent_double_spend():
    # 1. Simulate an attacker launching 2 concurrent withdrawal requests 
    # for $100, but the account ONLY has $100 total.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(withdraw_funds, 100)
        future2 = executor.submit(withdraw_funds, 100)
        
        result1 = future1.result()
        result2 = future2.result()

    # 2. THE ASSERTION: Exactly ONE transaction must succeed, and ONE must fail.
    # If both succeed, the attacker just printed free money.
    assert (result1 and not result2) or (not result1 and result2), "CRITICAL: Double Spend attack succeeded!"
    
    # 3. THE ASSERTION: The balance must safely rest at $0, NEVER negative.
    final_balance = DATABASE["account_123_balance"]
    assert final_balance == 0, f"CRITICAL: Database corruption! Balance is {final_balance}"
    
    print("\n[SUCCESS] Race condition mitigated. Atomic Mutex locking prevented the Double Spend.")
