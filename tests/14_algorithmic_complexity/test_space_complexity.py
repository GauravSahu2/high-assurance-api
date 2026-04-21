import tracemalloc


# Simulated memory allocation for a database query
def load_data_into_memory(data_size):
    # Simulating loading records into a list
    dataset = [i for i in range(data_size)]
    return len(dataset)


def test_linear_memory_scaling():
    # Start tracing RAM usage
    tracemalloc.start()

    # 1. Measure Peak RAM for 100,000 records
    load_data_into_memory(100_000)
    _, peak_small = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()  # Reset the tracker

    # 2. Measure Peak RAM for 1,000,000 records (10x larger)
    load_data_into_memory(1_000_000)
    _, peak_large = tracemalloc.get_traced_memory()

    tracemalloc.stop()

    # 3. Calculate the Memory Allocation Ratio
    memory_ratio = peak_large / peak_small

    # THE ASSERTION: 10x data should use exactly 10x memory.
    # If it uses significantly more, the code is duplicating data in memory.
    assert (
        memory_ratio < 15
    ), f"CRITICAL: Space Complexity violation (Memory Leak)! RAM scaled by {memory_ratio:.2f}x."
    print(
        f"\n[SUCCESS] Memory allocation scales safely in O(N) space. Peak RAM multiplier: {memory_ratio:.2f}x."
    )
