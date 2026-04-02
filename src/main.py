"""
High-Assurance API — main application module.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import random
import time
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import boto3
import jwt
import redis
import structlog
from botocore.exceptions import ClientError
from flask import Flask, g, jsonify, request
from logger import logger
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from security import apply_security_headers
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

app = Flask(__name__)

# ── Redis State Backend ────────────────────────────────────────────────────────
if os.environ.get("TEST_MODE"):
    import fakeredis

    redis_client = fakeredis.FakeStrictRedis(decode_responses=True)
else:  # pragma: no cover
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(
        redis_url,
        decode_responses=True,
        socket_timeout=2.0,
        socket_connect_timeout=2.0,
        max_connections=50,
    )


def init_db():
    if not redis_client.exists("balance:admin"):
        redis_client.set("balance:admin", 1000.0)
        redis_client.set("balance:user_1", 1000.0)
        redis_client.set("balance:user_2", 500.0)


init_db()


# ── Secrets Manager ────────────────────────────────────────────────────────────
def _load_secret(secret_name: str, fallback: str = "") -> str:
    try:
        region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        return response.get("SecretString", fallback)
    except ClientError:  # pragma: no cover
        return fallback
    except Exception:  # pragma: no cover
        return fallback


JWT_SECRET: str = _load_secret(
    "high-assurance-api/jwt-secret",
    fallback=os.environ.get("JWT_SECRET", "super-secure-dev-secret-key-12345"),
)


def _hash_password(password: str) -> str:
    """Hash password using native bcrypt (includes automatic salting)."""
    rounds = 4 if os.environ.get("TEST_MODE") else 12
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)
    ).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):  # pragma: no cover
        return False


USERS: dict = {
    "admin": {"password_hash": _hash_password("password123"), "role": "admin"},
    "user_1": {"password_hash": _hash_password("password111"), "role": "user"},
    "user_2": {"password_hash": _hash_password("password222"), "role": "user"},
}
DUMMY_HASH: str = _hash_password("dummy_constant_time_string")

MIN_TRANSFER: float = 1e-6
MAX_TRANSFER: float = 1_000.0
MAX_FAILED_ATTEMPTS: int = 5

ALLOWED_ORIGINS: list = [
    "http://localhost:3000",
    "https://trusted-bank.com",
]

flask_http_request_total = Counter(
    "flask_http_request_total",
    "Total HTTP requests counted by method, endpoint, and status",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
)

if not os.environ.get("TEST_MODE"):  # pragma: no cover
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        _provider = TracerProvider()
        _provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=os.environ.get(
                        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"
                    )
                )
            )
        )
        trace.set_tracer_provider(_provider)
        tracer = trace.get_tracer(__name__)
        FlaskInstrumentor().instrument_app(app)
    except Exception:
        pass


# ── Resilient Redis helpers ────────────────────────────────────────────────────
@retry(
    retry=retry_if_exception_type(redis.RedisError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
    reraise=True,
)
def _redis_get(key: str):
    return redis_client.get(key)


@retry(
    retry=retry_if_exception_type(redis.RedisError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
    reraise=True,
)
def _redis_ping():
    return redis_client.ping()


# ── JWT helpers ────────────────────────────────────────────────────────────────
def generate_jwt(username: str) -> str:
    now = datetime.now(UTC)
    role = USERS.get(username, {}).get("role", "user")
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=3600),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_jwt(token) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


def _extract_bearer(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0] != "Bearer" or not parts[1]:
        return None
    return parts[1]


# ── Hooks ──────────────────────────────────────────────────────────────────────
@app.before_request
def _before_request() -> None:
    g.start_time = time.time()
    g.correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        correlation_id=g.correlation_id, method=request.method, path=request.path
    )


@app.after_request
def _after_request(response):
    latency = time.time() - g.get("start_time", time.time())
    flask_http_request_total.labels(
        method=request.method, endpoint=request.path, status=response.status_code
    ).inc()
    http_request_duration_seconds.labels(endpoint=request.path).observe(latency)

    response.headers["X-Correlation-ID"] = g.get("correlation_id", "")
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Idempotency-Key, X-Correlation-ID"
        )

    return apply_security_headers(response)


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({"message": "API running"})


@app.route("/openapi.yaml")
def openapi_yaml():
    spec_path = os.path.join(os.path.dirname(__file__), "..", "openapi.yaml")
    try:
        with open(os.path.abspath(spec_path)) as fh:
            return fh.read(), 200, {"Content-Type": "text/yaml"}
    except FileNotFoundError:  # pragma: no cover
        return jsonify({"error": "spec not found"}), 404


@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    if os.environ.get("CHAOS_MODE", "").lower() == "true" and random.random() < 0.5:
        return jsonify({"status": "chaos"}), 503

    try:
        _redis_ping()
    except redis.RedisError:  # pragma: no cover
        return jsonify({"status": "degraded", "redis": "unreachable"}), 503

    return jsonify({"status": "ok"})


@app.route("/metrics")
def metrics_endpoint():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/login", methods=["POST"])
def login():
    ip: str = request.remote_addr or "unknown"
    lockout_key = f"lockout:{ip}"

    try:
        attempts = int(_redis_get(lockout_key) or 0)
        if attempts >= MAX_FAILED_ATTEMPTS:
            return jsonify({"error": "too many failed attempts"}), 429
    except redis.RedisError:  # pragma: no cover
        pass

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    username = body.get("username", "")
    password = body.get("password", "")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "invalid payload types"}), 400

    user = USERS.get(username)
    actual_hash = user["password_hash"] if user else DUMMY_HASH
    is_valid = _verify_password(password, actual_hash)

    if not user or not is_valid:
        try:
            redis_client.incr(lockout_key)
            redis_client.expire(lockout_key, 3600)
        except redis.RedisError:  # pragma: no cover
            pass
        logger.warning("authentication_failed", user_id=username, ip_address=ip)
        return jsonify({"error": "invalid credentials"}), 401

    try:
        redis_client.delete(lockout_key)
    except redis.RedisError:  # pragma: no cover
        pass

    return jsonify({"token": generate_jwt(username)})


@app.route("/transfer", methods=["POST"])
def transfer():
    raw_token = _extract_bearer(request.headers.get("Authorization"))
    if not raw_token:
        return jsonify({"error": "missing or malformed authorization header"}), 401

    claims = verify_jwt(raw_token)
    if not claims:
        return jsonify({"error": "invalid or expired token"}), 401

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    idempotency_key = request.headers.get("X-Idempotency-Key")
    idem_key = f"idem:{idempotency_key}" if idempotency_key else None

    if idem_key and redis_client.get(idem_key):
        return jsonify({"error": "duplicate transaction"}), 409

    raw_amount = body.get("amount")
    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a number"}), 400

    if amount < MIN_TRANSFER or amount > MAX_TRANSFER:
        return jsonify({"error": "amount out of range"}), 400

    username = claims["sub"]
    balance_key = f"balance:{username}"

    if not redis_client.exists(balance_key):  # pragma: no cover
        return jsonify({"error": "account not found"}), 404

    try:
        with redis_client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(balance_key)
                    balance = float(pipe.get(balance_key))
                    if balance < amount:
                        pipe.unwatch()
                        return jsonify({"error": "insufficient funds"}), 400

                    pipe.multi()
                    pipe.set(balance_key, balance - amount)
                    pipe.execute()
                    new_balance = balance - amount
                    break
                except redis.WatchError:  # pragma: no cover
                    continue
    except Exception:  # pragma: no cover
        return jsonify({"error": "transaction failed"}), 500

    if idem_key:
        redis_client.setex(idem_key, 86400, "processed")

    logger.info(
        "transaction_complete", user_id=username, amount=amount, new_balance=new_balance
    )

    return jsonify({"status": "transferred", "new_balance": new_balance})


@app.route("/api/users/<user_id>")
def get_user(user_id: str):
    raw_token = _extract_bearer(request.headers.get("Authorization"))
    if not raw_token:
        return jsonify({"error": "unauthorized"}), 401

    claims = verify_jwt(raw_token)
    if not claims:
        return jsonify({"error": "unauthorized"}), 401

    if claims.get("role") != "admin" and claims.get("sub") != user_id:
        return jsonify({"error": "forbidden"}), 403

    if user_id not in USERS:
        return jsonify({"error": "user not found"}), 404

    return jsonify({"user_id": user_id, "role": USERS[user_id]["role"]})


@app.route("/api/accounts/<user_id>/balance")
def get_balance(user_id: str):
    raw_token = _extract_bearer(request.headers.get("Authorization"))
    if not raw_token:
        return jsonify({"error": "unauthorized"}), 401

    claims = verify_jwt(raw_token)
    if not claims:
        return jsonify({"error": "unauthorized"}), 401

    if claims.get("role") != "admin" and claims.get("sub") != user_id:
        return jsonify({"error": "forbidden"}), 403

    balance_val = redis_client.get(f"balance:{user_id}")
    if balance_val is None:
        return jsonify({"error": "account not found"}), 404

    return jsonify({"user_id": user_id, "balance": float(balance_val)})


@app.route("/test/reset", methods=["POST"])
def reset_state():
    if not os.environ.get("TEST_MODE"):
        return jsonify({"error": "not found"}), 404
    redis_client.flushdb()
    init_db()
    return jsonify({"status": "test_state_reset"})


@app.errorhandler(redis.RedisError)
def handle_redis_error(_e):
    return jsonify({"error": "service temporarily degraded"}), 503


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):  # pragma: no cover
    response = jsonify({"error": "method not allowed"})
    response.status_code = 405
    if hasattr(e, "valid_methods") and e.valid_methods:  # pragma: no cover
        response.headers["Allow"] = ", ".join(sorted(e.valid_methods))
    return response


if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=5000)
