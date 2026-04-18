import gc
import uuid


def test_transfer_speed(benchmark, client, auth_header):
    def make_transfer():
        res = client.post(
            "/transfer",
            json={"amount": 1.0, "to_user": "user_2"},
            headers={**auth_header, "X-Idempotency-Key": str(uuid.uuid4())},
        )
        # Force the generator to close and release the DB connection immediately
        gc.collect()
        return res

    # Limit the benchmark to a safe number of iterations to prevent local DDoS
    result = benchmark.pedantic(make_transfer, rounds=10, iterations=5)
    assert result.status_code in [200, 201]
