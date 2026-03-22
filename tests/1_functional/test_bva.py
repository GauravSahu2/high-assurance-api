import pytest  # noqa: E402


@pytest.mark.parametrize(
    "amount, expected_status",
    [(0.000001, 200), (0.0000009, 400), (500.00, 200), (1000.00, 200), (1000.01, 400), ("fifty", 400)],
)
def test_boundary_values_live(client, auth_header, amount, expected_status):
    headers = {**auth_header, "X-Idempotency-Key": f"bva-{amount}-{expected_status}"}
    res = client.post("/transfer", json={"amount": amount}, headers=headers)
    assert res.status_code == expected_status


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def enforce_bva_state_locally():
    """Hyper-local state reset to defeat mutmut import shadowing"""
    import main as m

    if hasattr(m, "accounts"):
        m.accounts["user_1"] = 1000.0
        m.accounts["user_2"] = 500.0
        m.processed_transactions.clear()
        m.failed_login_attempts.clear()
