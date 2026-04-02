import uuid

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


@given(
    amount=st.one_of(
        st.floats(allow_nan=False, allow_infinity=False),
        st.integers(),
        st.text(),
        st.none(),
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_fuzz_transfer_endpoint(client, auth_header, amount):
    headers = {**auth_header, "X-Idempotency-Key": str(uuid.uuid4())}
    payload = {"amount": amount}
    res = client.post("/transfer", json=payload, headers=headers)
    assert res.status_code in (200, 400, 409)
