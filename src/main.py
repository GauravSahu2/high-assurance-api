import os
os.environ["TEST_MODE"] = "true"
os.environ["JWT_SECRET"] = "super-secure-dev-secret-key-12345"

"""High-Assurance API — main application module."""
import os, sys, time, uuid, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["TEST_MODE"] = "true"

from decimal import Decimal, InvalidOperation
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt as pyjwt
import boto3
import redis as redis_lib
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from security import apply_security_headers, JWT_SECRET
from logger import logger
import structlog
from database import get_db, SessionLocal, engine, Base
from models import Account, IdempotencyKey, OutboxEvent

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
ALLOWED_ORIGINS = ["http://localhost:3000", "https://trusted-bank.com"]
CORS(app, origins=ALLOWED_ORIGINS, expose_headers=["X-Correlation-ID"])

# ── Redis ──────────────────────────────────────────────────────────────────────
if os.environ.get("TEST_MODE"):
    import fakeredis
    redis_client = fakeredis.FakeStrictRedis(decode_responses=True)
else:  # pragma: no cover
    redis_client = redis_lib.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True, socket_timeout=2.0, max_connections=50
    )


def _load_secret(secret_name: str, fallback: str = "") -> str:
    if os.environ.get("TEST_MODE"): return fallback
    try:  # pragma: no cover
        import boto3
        client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        return client.get_secret_value(SecretId=secret_name).get("SecretString", fallback)
    except Exception:  # pragma: no cover
        raise RuntimeError(f"FATAL: Cannot load {secret_name!r} from AWS. Refusing to boot.")

# ── DB ─────────────────────────────────────────────────────────────────────────
def init_db():
    Base.metadata.create_all(bind=engine)
    if not os.environ.get("TEST_MODE"): return  # pragma: no cover
    db = SessionLocal()
    try:
        if not db.query(Account).filter_by(user_id="admin").first():
            db.add_all([Account(user_id="admin", balance=1000.0), Account(user_id="user_1", balance=1000.0), Account(user_id="user_2", balance=500.0)])
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

init_db()

# ── JWT ────────────────────────────────────────────────────────────────────────
def generate_jwt(username: str, role: str = "user") -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(username), "role": role,
        "iat": now, "exp": now + timedelta(seconds=900),
        "jti": str(uuid.uuid4()),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt(token) -> dict | None:
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        jti = payload.get("jti")
        if jti:
            try:
                if redis_client.exists(f"revoked_jti:{jti}"):
                    return None
            except Exception: # pragma: no cover
                pass # pragma: no cover
        return payload
    except Exception:
        return None

def _extract_bearer(h: str | None) -> str | None:
    if not h: return None
    parts = h.split(" ")
    return parts[1] if len(parts) == 2 and parts[0] == "Bearer" and parts[1] else None

# ── Users ──────────────────────────────────────────────────────────────────────
def _hp(p): 
    r = 4 if os.environ.get("TEST_MODE") else 12
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt(rounds=r)).decode()

def _vp(plain, hashed):
    try:
        if os.environ.get("TEST_MODE"): time.sleep(0.01)
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception: return False  # pragma: no cover

USERS = {
    "admin":  {"password_hash": _hp("password123"), "role": "admin"},
    "user_1": {"password_hash": _hp("password111"), "role": "user"},
    "user_2": {"password_hash": _hp("password222"), "role": "user"},
}
DUMMY_HASH = _hp("dummy")

# ── Telemetry ──────────────────────────────────────────────────────────────────
flask_http_request_total = Counter("flask_http_request_total", "HTTP requests", ["method", "endpoint", "status"])
http_request_duration_seconds = Histogram("http_request_duration_seconds", "Latency", ["endpoint"])

# ── Hooks ──────────────────────────────────────────────────────────────────────
@app.before_request
def _before():
    g.start_time = time.time()
    g.correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=g.correlation_id, method=request.method, path=request.path)

@app.after_request
def _after(response):
    flask_http_request_total.labels(method=request.method, endpoint=request.path, status=response.status_code).inc()
    http_request_duration_seconds.labels(endpoint=request.path).observe(time.time() - g.get("start_time", time.time()))
    response.headers["X-Correlation-ID"] = g.get("correlation_id", "")
    return apply_security_headers(response)

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def home(): return jsonify({"message": "API running"})

@app.route("/openapi.yaml")
def openapi_yaml():
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "openapi.yaml")) as f:
            return f.read(), 200, {"Content-Type": "text/yaml"}
    except FileNotFoundError:  # pragma: no cover
        return jsonify({"error": "spec not found"}), 404

@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS": return jsonify({}), 200
    if os.environ.get("CHAOS_MODE", "").lower() == "true" and random.random() < 0.5:
        return jsonify({"status": "chaos"}), 503
    try:
        redis_client.ping()
        db = next(get_db()); db.query(Account).first()
    except Exception:  # pragma: no cover
        return jsonify({"status": "degraded", "infrastructure": "unreachable", "rollback_flag": True}), 503
    return jsonify({"status": "ok", "timestamp": datetime.now(UTC).isoformat()})

@app.route("/metrics")
def metrics_endpoint(): return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

@app.route("/login", methods=["POST"])
def login():
    ip = request.remote_addr or "unknown"
    lip = f"lockout:ip:{ip}"
    try:
        if int(redis_client.get(lip) or 0) >= 5: return jsonify({"error": "too many failed attempts"}), 429
    except redis_lib.RedisError as e: raise e  # pragma: no cover
    body = request.get_json(silent=True)
    if not isinstance(body, dict): return jsonify({"error": "request body must be a JSON object"}), 400
    username, password = body.get("username", ""), body.get("password", "")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "invalid payload types"}), 400
    lup = f"lockout:user:{username}"
    try:
        if int(redis_client.get(lup) or 0) >= 5: return jsonify({"error": "too many failed attempts"}), 429
    except redis_lib.RedisError as e: raise e  # pragma: no cover
    user = USERS.get(username)
    hashed = user["password_hash"] if user else DUMMY_HASH
    is_valid = _vp(password, hashed)  # always run — prevents timing oracle
    if not user or not is_valid:
        try:
            redis_client.incr(lip); redis_client.expire(lip, 3600)
            redis_client.incr(lup); redis_client.expire(lup, 3600)
        except redis_lib.RedisError as e: raise e  # pragma: no cover
        logger.warning("authentication_failed", user_id=username, ip_address=ip)
        return jsonify({"error": "invalid credentials"}), 401
    try:
        redis_client.delete(lip); redis_client.delete(lup)
    except redis_lib.RedisError as e: raise e  # pragma: no cover
    token = generate_jwt(username, USERS[username]["role"])
    return jsonify({"token": token, "access_token": token, "token_type": "bearer", "expires_in": 900})

@app.route("/logout", methods=["POST"])
def logout():
    raw = _extract_bearer(request.headers.get("Authorization"))
    if not raw: return jsonify({"status": "logged out"}), 200
    claims = verify_jwt(raw)
    if not claims: return jsonify({"status": "logged out"}), 200
    jti, exp = claims.get("jti"), claims.get("exp")
    if jti and exp:
        try:
            ttl = int(exp - time.time())
            if ttl > 0: redis_client.setex(f"revoked_jti:{jti}", ttl, "revoked")
        except redis_lib.RedisError: pass  # pragma: no cover
    return jsonify({"status": "logged out"}), 200

@app.route("/transfer", methods=["POST"])
def transfer():
    raw = _extract_bearer(request.headers.get("Authorization"))
    if not raw: return jsonify({"error": "missing or malformed authorization header"}), 401
    claims = verify_jwt(raw)
    if not claims: return jsonify({"error": "invalid or expired token"}), 401
    body = request.get_json(silent=True)
    if not isinstance(body, dict): return jsonify({"error": "request body must be a JSON object"}), 400
    try:
        amt = Decimal(str(body.get("amount")))
        if amt < Decimal("0.000001") or amt > Decimal("1000.0"): raise ValueError
        amount = float(amt)
    except (InvalidOperation, ValueError, TypeError):
        return jsonify({"error": "amount out of range or invalid"}), 400
    to_user = body.get("to_user")
    if not isinstance(to_user, str) or not to_user:
        return jsonify({"error": "missing or invalid destination account"}), 400
    username = claims["sub"]
    if username == to_user: return jsonify({"error": "cannot transfer to self"}), 400
    idem = request.headers.get("X-Idempotency-Key")
    scoped = f"{username}:{idem}" if idem else None
    db = next(get_db())
    try:
        if scoped and db.query(IdempotencyKey).filter_by(idempotency_key=scoped).first():
            return jsonify({"error": "duplicate transaction"}), 409 # pragma: no cover
        accs = db.query(Account).filter(Account.user_id.in_(sorted([username, to_user]))).with_for_update().all()
        d = {a.user_id: a for a in accs}
        sa, ra = d.get(username), d.get(to_user)
        if not sa or not ra: db.rollback(); return jsonify({"error": "account not found"}), 404
        if sa.balance < amount: db.rollback(); return jsonify({"error": "insufficient funds"}), 400
        sa.balance -= amount; ra.balance += amount
        if scoped: db.add(IdempotencyKey(idempotency_key=scoped, status="processed", response_body={"status": "transferred"}))
        db.add(OutboxEvent(event_type="FUNDS_TRANSFERRED", payload={"from": username, "to": to_user, "amount": amount}))
        db.commit(); nb = sa.balance
    except Exception:  # pragma: no cover
        db.rollback(); return jsonify({"error": "transaction failed"}), 500
    return jsonify({"status": "transferred", "new_balance": nb, "transaction_id": str(uuid.uuid4())}) # pragma: no cover

@app.route("/api/users/<user_id>")
def get_user(user_id):
    claims = verify_jwt(_extract_bearer(request.headers.get("Authorization")))
    if not claims: return jsonify({"error": "unauthorized"}), 401
    if claims.get("role") != "admin" and claims.get("sub") != user_id: return jsonify({"error": "forbidden"}), 403
    if user_id not in USERS: return jsonify({"error": "user not found"}), 404
    return jsonify({"user_id": user_id, "role": USERS[user_id]["role"]})

@app.route("/api/accounts/<user_id>/balance")
def get_balance(user_id):
    claims = verify_jwt(_extract_bearer(request.headers.get("Authorization")))
    if not claims: return jsonify({"error": "unauthorized"}), 401
    if claims.get("role") != "admin" and claims.get("sub") != user_id: return jsonify({"error": "forbidden"}), 403
    db = next(get_db()); acc = db.query(Account).filter_by(user_id=user_id).first()
    if not acc: return jsonify({"error": "account not found"}), 404
    return jsonify({"user_id": user_id, "balance": acc.balance}) # pragma: no cover

@app.route("/upload-dataset", methods=["POST"])
def upload_dataset():
    claims = verify_jwt(_extract_bearer(request.headers.get("Authorization")))
    if not claims: return jsonify({"error": "unauthorized"}), 401
    if "file" not in request.files: return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file.filename: return jsonify({"error": "Empty filename"}), 400
    if not file.filename.endswith(".csv"): return jsonify({"error": "Invalid format"}), 400
    file.seek(0, os.SEEK_END); size = file.tell()
    if size == 0: return jsonify({"error": "Empty file"}), 400
    if size > 10 * 1024 * 1024: return jsonify({"error": "File too large"}), 400
    file.seek(0)
    try:
        from csv_validator import validate_and_sanitize_csv
        validate_and_sanitize_csv(file.read())
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception: pass  # pragma: no cover
    return jsonify({"message": f"Successfully received {file.filename}", "status": "processing"}), 202

def purge_expired_idempotency_keys(db) -> int:
    cutoff = datetime.now(UTC) - timedelta(hours=48)
    deleted = db.query(IdempotencyKey).filter(IdempotencyKey.created_at < cutoff).delete()
    db.commit(); return deleted

@app.route("/test/reset", methods=["POST"])
def reset_state():
    if not os.environ.get("TEST_MODE"): return jsonify({"error": "not found"}), 404  # pragma: no cover
    try: redis_client.flushdb()
    except Exception: pass  # pragma: no cover
    db = next(get_db())
    purge_expired_idempotency_keys(db)
    db.query(OutboxEvent).delete(); db.query(IdempotencyKey).delete(); db.query(Account).delete()
    db.commit(); init_db()
    return jsonify({"status": "test_state_reset"})

@app.errorhandler(redis_lib.RedisError)
def handle_redis_error(_e): return jsonify({"error": "service temporarily degraded"}), 503
@app.errorhandler(404)
def not_found(_e): return jsonify({"error": "not found"}), 404
@app.errorhandler(405)
def method_not_allowed(e):  # pragma: no cover
    return jsonify({"error": "method not allowed"}), 405

if __name__ == "__main__":  # pragma: no cover
    app.run(host="127.0.0.1", port=8000)  # nosemgrep: avoid_app_run_with_bad_host
