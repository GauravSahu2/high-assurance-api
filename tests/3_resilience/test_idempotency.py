import uuid

# Simulated Database and API Endpoint
PROCESSED_REQUESTS = {}
ACCOUNT_BALANCE = 1000


def mock_transfer_api(request_id, amount):
    global ACCOUNT_BALANCE

    # IDEMPOTENCY CHECK: If we've seen this exact request ID before, do NOT charge again!
    if request_id in PROCESSED_REQUESTS:
        return 200, "Already Processed (Idempotent Response)"

    # Process new request
    ACCOUNT_BALANCE -= amount
    PROCESSED_REQUESTS[request_id] = True
    return 200, "Success"


def test_idempotency_network_glitch():
    global ACCOUNT_BALANCE
    ACCOUNT_BALANCE = 1000  # Reset balance

    # Generate a unique ID for this specific transaction
    glitch_uuid = str(uuid.uuid4())

    # Action 1: User clicks "Transfer $500"
    status1, msg1 = mock_transfer_api(glitch_uuid, 500)

    # Action 2: Network lags, mobile app automatically retries the EXACT same request 50ms later
    status2, msg2 = mock_transfer_api(glitch_uuid, 500)

    # Both should return 200 OK so the app doesn't crash, BUT balance should only drop by 500, not 1000.
    assert status1 == 200
    assert status2 == 200
    assert ACCOUNT_BALANCE == 500, f"CRITICAL: Double charge occurred! Balance is {ACCOUNT_BALANCE}"

    print("\n[SUCCESS] Idempotency enforced. Network retry did not result in a double charge.")
