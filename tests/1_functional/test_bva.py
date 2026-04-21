import pytest


@pytest.mark.parametrize(
    "amount, expected_status",
    [
        (0.000001, 200),
        (0.0000009, 400),
        (500.00, 200),
        (1000.00, 200),
        (1000.01, 400),
        ("fifty", 400),
    ],
)
def test_boundary_values_live(client, auth_header, amount, expected_status):
    headers = {**auth_header, "X-Idempotency-Key": f"bva-{amount}-{expected_status}"}
    res = client.post("/transfer", json={"amount": amount, "to_user": "user_2"}, headers=headers)
    assert res.status_code == expected_status
