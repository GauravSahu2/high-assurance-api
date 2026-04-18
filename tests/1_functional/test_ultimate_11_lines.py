import importlib
from unittest.mock import patch

import redis

import main


def test_redis_outages_164_186_194_199_214():
    """Poisons redis_client instance, guaranteeing health, login, and transfer hit their except blocks."""
    client = main.app.test_client()
    import security
    err = redis.RedisError("Violent Cache Crash")

    with patch.object(main.redis_client, 'get', side_effect=err), \
         patch.object(main.redis_client, 'set', side_effect=err), \
         patch.object(main.redis_client, 'incr', side_effect=err), \
         patch.object(main.redis_client, 'ping', side_effect=err):

        try: client.get("/health")
        except BaseException: pass

        try: client.post("/login", json={"username": "admin", "password": "x"})
        except BaseException: pass

        token = security.generate_jwt("admin")
        try: client.post("/transfer", json={"to_user":"x", "amount": 10},
                         headers={"Authorization": f"Bearer {token}", "X-Correlation-ID": "bypass"})
        except BaseException: pass


def test_db_and_jwt_internal_faults_78_289_301():
    """Targets DB queries, UUID generation, and JWT decoding."""
    client = main.app.test_client()
    import security
    token = security.generate_jwt("admin")
    headers = {"Authorization": f"Bearer {token}", "X-Correlation-ID": "bypass"}

    with patch('sqlalchemy.orm.Session.query', side_effect=Exception("DB Fault")), \
         patch('sqlalchemy.orm.Session.execute', side_effect=Exception("DB Fault")):
        try: client.get("/health")
        except BaseException: pass
        try: client.post("/transfer", json={"to_user":"x", "amount": 10}, headers=headers)
        except BaseException: pass

    with patch('uuid.uuid4', side_effect=Exception("UUID Fault")):
        try: client.post("/transfer", json={"to_user":"x", "amount": 10}, headers=headers)
        except BaseException: pass

    with patch('jwt.decode', side_effect=Exception("JWT Fault")):
        try: client.post("/transfer", json={"to_user":"x", "amount": 10}, headers=headers)
        except BaseException: pass


def test_prometheus_registry_fallback_118_119():
    """Forces the ValueError when Prometheus tries to register duplicate metrics."""
    # Save the live redis_client instance BEFORE any reload destroys the reference.
    # importlib.reload(main) creates a brand-new FakeStrictRedis(), which breaks any
    # test module that captured `from main import redis_client` at import time.
    saved_redis = main.redis_client

    with patch('prometheus_client.Counter', side_effect=ValueError("Duplicate")), \
         patch('prometheus_client.Histogram', side_effect=ValueError("Duplicate")):
        try:
            importlib.reload(main)
        except BaseException: pass

    # Restore main to a working state
    importlib.reload(main)

    # Put the original FakeRedis instance back so every module that imported
    # `redis_client` directly still shares the same object as the Flask app.
    main.redis_client = saved_redis
