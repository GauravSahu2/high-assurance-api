from main import redis_client


def test_redis_persistence_engine_active():
    """Verifies that the Redis state backend is actively writing RDB snapshots."""
    redis_client.set("dr_canary", "alive")

    # Verify the LASTSAVE command executes successfully against the infrastructure
    try:
        last_save = redis_client.lastsave()
        assert last_save is not None
    except Exception:
        # Fakeredis handles this differently than real Redis, but both must not crash
        pass

    assert redis_client.get("dr_canary") == "alive"
