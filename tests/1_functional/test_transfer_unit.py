from datetime import UTC


def make_token(client, username="admin", password="password123"):
    res = client.post("/login", json={"username": username, "password": password})
    return res.get_json()["token"]


def test_transfer_succeeds(client):
    token = make_token(client)
    res = client.post(
        "/transfer",
        json={"amount": 100.0, "to_user": "user_2"},
        headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": "key-001"},
    )
    assert res.status_code == 200
    assert res.get_json()["new_balance"] == 900.0


def test_transfer_rejects_above_maximum(client):
    token = make_token(client)
    res = client.post(
        "/transfer",
        json={"amount": 1000.01, "to_user": "user_2"},
        headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": "key-002"},
    )
    assert res.status_code == 400


def test_transfer_duplicate_idempotency_key(client):
    token = make_token(client)
    headers = {"Authorization": f"Bearer {token}", "X-Idempotency-Key": "key-003"}
    client.post("/transfer", json={"amount": 1.0, "to_user": "user_2"}, headers=headers)
    res = client.post("/transfer", json={"amount": 1.0, "to_user": "user_2"}, headers=headers)
    assert res.status_code == 409


def test_login_payload_claims_kill_mutants(client):
    """Assassin test to kill generate_jwt dictionary mutants."""
    from auth import verify_jwt

    # Hit the real endpoint to trigger generate_jwt()
    res = client.post("/login", json={"username": "admin", "password": "password123"})
    assert res.status_code == 200
    token = res.get_json()["token"]

    # Decode it using the system's own verification logic (which handles PASETO/JWT)
    payload = verify_jwt(token)

    # 🔪 Kill Mutant #5 (role -> ROLE)
    assert "role" in payload, "Mutant survived: 'role' key missing"
    assert payload["role"] == "admin"

    # 🔪 Kill the sibling mutants ("sub" -> "SUB", "exp" -> "EXP", etc.)
    assert "sub" in payload
    assert payload["sub"] == "admin"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_strict_time_boundaries(client):
    """Sniper test to kill all time-traveling mutants in generate_jwt."""
    from auth import verify_jwt

    res = client.post("/login", json={"username": "admin", "password": "password123"})
    token = res.get_json()["token"]

    payload = verify_jwt(token)

    # 🔪 Kill Mutants 11, 12, 16, 18, 21, 27
    time_difference = payload["exp"] - payload["iat"]
    # The default expiry in config.py is 900
    assert time_difference == 900, f"Mutant survived! Expected 900s, got {time_difference}s"


def test_jwt_iat_is_utc(client):
    """Kills Mutant 21: Proves the token generation is strictly UTC, not Local Time."""
    from datetime import datetime

    from auth import verify_jwt

    res = client.post("/login", json={"username": "admin", "password": "password123"})
    token = res.get_json()["token"]
    payload = verify_jwt(token)

    now_utc = datetime.now(UTC).timestamp()
    assert abs(payload["iat"] - now_utc) < 60, "Mutant survived: iat timezone is not UTC!"


def test_jwt_encode_explicit_algorithm():
    """Kills Mutant 27: Ensures the encoding logic uses high-assurance primitives."""
    from auth import generate_jwt, verify_jwt

    token = generate_jwt("admin")
    # Verify it is a PASETO v4.public token
    assert token.startswith("v4.public."), "High-Assurance requirement: Must use PASETO v4.public"

    payload = verify_jwt(token)
    assert payload["sub"] == "admin"


def test_verify_jwt_format_mutants(client):
    """Kills Mutants 1 & 9: Strict header parsing checks."""
    res_login = client.post("/login", json={"username": "admin", "password": "password123"})
    valid_token = res_login.get_json()["token"]

    # 🔪 Kill Mutant 1: Send a valid token, but with the wrong prefix (Basic)
    res1 = client.get("/api/users/user_1", headers={"Authorization": f"Basic {valid_token}"})
    assert res1.status_code == 401, "Mutant 1 survived: 'Basic' prefix bypassed the Bearer check!"

    # 🔪 Kill Mutant 9: Send a valid token, but with a double-space
    res2 = client.get("/api/users/user_1", headers={"Authorization": f"Bearer  {valid_token}"})
    assert res2.status_code == 401, "Mutant 9 survived: split(None) allowed a malformed double-space!"


def test_jwt_regular_user_role():
    """Kills Mutants 11 & 12: Direct unit test bypassing the /login route constraints."""
    from auth import generate_jwt, verify_jwt

    # Call the function directly with a non-admin username
    token = generate_jwt("user_1")
    payload = verify_jwt(token)

    assert payload["role"] == "user", "Mutant survived: Non-admin role was tampered with!"


def test_jwt_absolute_time_strictness():
    """Kills Equivalent Timezone Mutants by forcing an environment shift."""
    import os
    import time
    from datetime import datetime

    from auth import generate_jwt, verify_jwt

    # 1. Save current TZ and warp to New York
    old_tz = os.environ.get("TZ")
    os.environ["TZ"] = "EST5EDT"
    time.tzset()

    try:
        # 2. Generate the token directly
        token = generate_jwt("admin")
        payload = verify_jwt(token)

        # 3. 🔪 Kill Mutant 16 (Strict 900s Delta)
        assert payload["exp"] - payload["iat"] == 900, "Time Delta Mutant survived!"

        # 4. 🔪 Kill Mutant 21 (Strict UTC Validation)
        now_utc = datetime.now(UTC).timestamp()
        assert abs(payload["iat"] - now_utc) < 5, "Timezone Mutant survived: Used local time!"
    finally:
        # 5. Restore the space-time continuum
        if old_tz:
            os.environ["TZ"] = old_tz
        else:
            try:
                del os.environ["TZ"]
            except KeyError:
                pass
        time.tzset()
