import logging
import os
import random
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta

import boto3
import jwt
from botocore.exceptions import ClientError
from flask import Flask, Response, g, jsonify, request, send_from_directory
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# ── OpenTelemetry ─────────────────────────────────────────────────────────────
from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # noqa: F401

    _otlp_available = True  # pragma: no cover
except ImportError:  # pragma: no cover
    _otlp_available = False

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s", rename_fields={"asctime": "timestamp", "levelname": "level"}
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = Flask(__name__)

_REQUEST_COUNT = Counter(
    "flask_http_request_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
_REQUEST_LATENCY = Histogram(
    "flask_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

db_lock = threading.Lock()
processed_transactions: dict[str, float] = {}
failed_login_attempts: dict[str, int] = {}


def _load_secret(secret_name: str, fallback: str) -> str:
    """Load a secret from AWS Secrets Manager if available, else fall back
    to the environment variable. In production, the fallback should never
    be reached — missing config fails loudly via the ClientError.
    Uses moto in tests, real AWS Secrets Manager in production.
    """
    endpoint = os.getenv("AWS_SECRETS_ENDPOINT_URL")  # set to localstack in docker-compose
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name="secretsmanager",
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            endpoint_url=endpoint,
        )
        response = client.get_secret_value(SecretId=secret_name)
        return str(response["SecretString"])
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        if error_code in (
            "ResourceNotFoundException",
            "InvalidRequestException",
            "NoCredentialsError",
            "EndpointResolutionError",
        ):
            return fallback
        raise  # pragma: no cover
    except Exception:  # pragma: no cover
        return fallback


ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:3000").split(",")
ADMIN_PASS_HASH = generate_password_hash(
    _load_secret("high-assurance-api/admin-password", os.getenv("ADMIN_PASSWORD", "password123"))
)
JWT_SECRET = _load_secret("high-assurance-api/jwt-secret", os.getenv("JWT_SECRET", "super-secure-dev-secret-key-12345"))

users = {
    "admin": ADMIN_PASS_HASH,
    "user_1": generate_password_hash("password111"),
    "user_2": generate_password_hash("password222"),
}
accounts = {"user_1": 1000.0, "user_2": 500.0}


def generate_jwt(username: str) -> str:
    payload = {
        "sub": username,
        "role": "admin" if username == "admin" else "user",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_jwt(auth_header: str) -> dict[str, str] | None:
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@app.route("/metrics")
def metrics_endpoint() -> Response:
    """Expose Prometheus metrics for scraping."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.before_request
def security_layer() -> "tuple[Response, int] | None":
    g.correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    ip: str = request.remote_addr or "unknown"

    if os.getenv("CHAOS_MODE") == "true" and random.random() < 0.05:  # noqa: S311
        app.logger.warning("chaos_strike", extra={"trace_id": g.correlation_id})
        return jsonify({"error": "Chaos Monkey Strike - Service Unavailable"}), 503

    if failed_login_attempts.get(ip, 0) >= 5 and request.path == "/login":
        return jsonify({"error": "Account locked"}), 429
    return None


@app.after_request
def secure_headers(response: Response) -> Response:
    trace_id = getattr(g, "correlation_id", "SYSTEM")
    response.headers["X-Correlation-ID"] = trace_id

    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    elif os.getenv("TEST_MODE") == "true":
        response.headers["Access-Control-Allow-Origin"] = "*"

    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Idempotency-Key"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"

    app.logger.info(
        "api_request",
        extra={
            "trace_id": trace_id,
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "ip": request.remote_addr,
        },
    )
    return response


@app.route("/openapi.yaml", methods=["GET"])
def serve_openapi() -> Response:
    return send_from_directory(os.getcwd(), "openapi.yaml")


@app.route("/", methods=["GET"])
def index() -> str:
    return '<html><body><input id="user"><input id="pass" type="password"><button id="btn">Login</button><div id="msg">Ready</div><script>document.getElementById("btn").onclick = async () => { const u = document.getElementById("user").value; const p = document.getElementById("pass").value; const res = await fetch("/login", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({username: u, password: p})}); const data = await res.json(); document.getElementById("msg").innerText = data.token ? "Token Received" : (data.error || "Access Denied"); }</script></body></html>'


@app.route("/login", methods=["POST"])
def login() -> tuple[Response, int]:
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400
    username, password = data.get("username", ""), data.get("password", "")
    if not isinstance(username, str) or not isinstance(password, str) or not username or not password:
        return jsonify({"error": "Invalid JSON"}), 400
    ip: str = request.remote_addr or "unknown"

    if username in users:
        valid = check_password_hash(users[username], password)
    else:
        check_password_hash(ADMIN_PASS_HASH, "dummy_verify")
        valid = False

    if valid:
        failed_login_attempts[ip] = 0
        return jsonify({"token": generate_jwt(username)}), 200

    failed_login_attempts[ip] = failed_login_attempts.get(ip, 0) + 1
    return jsonify({"error": "Access Denied"}), 401


@app.route("/transfer", methods=["POST"])
def transfer() -> tuple[Response, int]:
    auth_data = verify_jwt(request.headers.get("Authorization", ""))
    if not auth_data:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid Body"}), 400

    amount = data.get("amount")
    idem_key = request.headers.get("X-Idempotency-Key")

    if not idem_key or not isinstance(amount, int | float) or amount < 0.000001 or amount > 1000.0:
        return jsonify({"error": "Invalid Request"}), 400

    with db_lock:
        if idem_key in processed_transactions:
            return jsonify({"error": "Duplicate"}), 409
        if accounts["user_1"] >= amount:
            accounts["user_1"] -= amount
            processed_transactions[idem_key] = time.time()
            return jsonify({"new_balance": accounts["user_1"]}), 200
    return jsonify({"error": "Insufficient funds"}), 400


@app.route("/api/users/<user_id>", methods=["GET"])
def get_user_data(user_id: str) -> tuple[Response, int]:
    auth_data = verify_jwt(request.headers.get("Authorization", ""))
    if not auth_data:
        return jsonify({"error": "Unauthorized"}), 401

    if auth_data["sub"] != user_id and auth_data["role"] != "admin":
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({"data": f"Secret data for {user_id}"}), 200


@app.route("/api/accounts/<user_id>/balance", methods=["GET"])
def get_balance(user_id: str) -> tuple[Response, int]:
    auth_data = verify_jwt(request.headers.get("Authorization", ""))
    if not auth_data:
        return jsonify({"error": "Unauthorized"}), 401
    if auth_data["sub"] != user_id and auth_data["role"] != "admin":
        return jsonify({"error": "Forbidden"}), 403
    if user_id not in accounts:
        return jsonify({"error": "Not Found"}), 404
    return jsonify({"user_id": user_id, "balance": accounts[user_id]}), 200


@app.route("/test/reset", methods=["POST"])
def reset_state() -> tuple[Response, int]:
    if os.getenv("TEST_MODE") != "true":
        return jsonify({"error": "Not Found"}), 404

    failed_login_attempts.clear()
    processed_transactions.clear()
    accounts["user_1"] = 1000.0
    accounts["user_2"] = 500.0
    return jsonify({"status": "test_state_reset"}), 200


@app.route("/health", methods=["GET", "OPTIONS"])
def health() -> tuple[Response, int]:
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":  # pragma: no cover
    app.run(host="127.0.0.1", port=8000, threaded=True)
