import time


# Simulated API parsing logic
def parse_payload(data_size):
    # Simulating a safe O(N) operation (e.g., iterating through a JSON array once)
    total = 0
    for i in range(data_size):
        total += i
    return total


def test_linear_time_scaling():
    # 1. Baseline Test (100,000 records)
    start_small = time.perf_counter()
    parse_payload(100_000)
    time_small = time.perf_counter() - start_small

    # 2. Stress Test (1,000,000 records - Exactly 10x larger)
    start_large = time.perf_counter()
    parse_payload(1_000_000)
    time_large = time.perf_counter() - start_large

    # Prevent division by zero if execution was too fast
    if time_small == 0:
        time_small = 0.000001

    # 3. Calculate the Scaling Ratio
    scaling_ratio = time_large / time_small

    # THE ASSERTION: 10x data should take ~10x time.
    # We allow a buffer up to 25x for CPU background noise.
    # If it hits 50x or 100x, it's exponential and mathematically dangerous.
    assert (
        scaling_ratio < 25
    ), f"CRITICAL: CPU Time Complexity violation! Execution scaled exponentially by {scaling_ratio:.2f}x."
    print(
        f"\n[SUCCESS] CPU Execution scales safely in O(N) time. Scale multiplier: {scaling_ratio:.2f}x."
    )
