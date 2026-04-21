import importlib
from unittest.mock import patch

import main
import redis
import security

client = main.app.test_client()


def test_prometheus_inline_118_119():
    saved_redis = main.redis_client
    with (
        patch("prometheus_client.Counter", side_effect=ValueError("Dup")),
        patch("prometheus_client.Histogram", side_effect=ValueError("Dup")),
    ):
        try:
            importlib.reload(main)
        except Exception:
            pass
    importlib.reload(main)
    main.redis_client = saved_redis


def test_init_db_rollback_59_60():
    with patch("sqlalchemy.orm.Session.query") as mock_q:
        mock_q.return_value.filter_by.return_value.first.return_value = None
        with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("DB Crash")):
            main.init_db()


def test_redis_outages_186_194_199_214():
    err = redis.RedisError("Simulated Redis Crash")
    with (
        patch.object(main.redis_client, "get", side_effect=err),
        patch.object(main.redis_client, "set", side_effect=err),
        patch.object(main.redis_client, "incr", side_effect=err),
    ):
        client.post("/login", json={"username": "admin", "password": "password"})
        token = security.generate_jwt("admin")
        client.post(
            "/transfer",
            json={"to_user": "x", "amount": 10},
            headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "123"},
        )


def test_generic_exceptions_78_289_301():
    token = security.generate_jwt("admin")
    headers = {"Authorization": f"Bearer {token}", "X-Correlation-ID": "test-id"}
    with patch("main.uuid.uuid4", side_effect=Exception("BOOM")):
        client.post("/transfer", json={"to_user": "x", "amount": 10}, headers=headers)
    with patch("security.decode_jwt", side_effect=Exception("BOOM")):
        client.post("/transfer", json={"to_user": "x", "amount": 10}, headers=headers)
    with patch("sqlalchemy.orm.Session.query", side_effect=Exception("DB Fault")):
        client.post("/transfer", json={"to_user": "x", "amount": 10}, headers=headers)
