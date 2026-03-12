import pytest

# Mock function simulating the API's validation logic
def validate_transfer(amount):
    if not isinstance(amount, (int, float)):
        return 400
    if amount < 0.000001:
        return 400
    if amount > 1000000000:
        return 400
    return 200

@pytest.mark.parametrize("amount, expected_status", [
    (0.000001, 200),        # The exact lower boundary (PASS)
    (0.0000009, 400),       # Just below the boundary (FAIL)
    (500.00, 200),          # Normal Happy Path (PASS)
    (1000000000.00, 200),   # The exact upper boundary (PASS)
    (1000000000.01, 400),   # Just above the boundary (FAIL)
    ("fifty", 400)          # Negative Testing: Wrong data type (FAIL)
])
def test_boundary_values(amount, expected_status):
    assert validate_transfer(amount) == expected_status
