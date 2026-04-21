import importlib

import pytest

import main
from main import get_db


def test_get_db_yield_and_close():
    """Forces the generator to exhaust so the 'finally: db.close()' block is covered."""
    gen = get_db()
    db = next(gen)
    assert db is not None

    # Asking for the next item forces the generator to finish and run the finally block
    with pytest.raises(StopIteration):
        next(gen)


def test_inline_metric_duplicate_coverage():
    """
    Since main.py was already imported, the Prometheus metrics are in the REGISTRY.
    Reloading the module forces it to hit the ValueError and execute the except block!
    """
    saved_redis = main.redis_client
    importlib.reload(main)
    main.redis_client = saved_redis
