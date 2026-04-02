def test_transfer_speed(benchmark, client, auth_header):
    """Measures the exact latency of the transfer endpoint."""

    def make_transfer():
        return client.post("/transfer", json={"amount": 1.0}, headers=auth_header)

    result = benchmark(make_transfer)
    assert result.status_code in [200, 400, 409]  # Allow typical responses
