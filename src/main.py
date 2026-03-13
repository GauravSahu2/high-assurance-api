import uuid
import time
import logging
import os
import threading
import json
from flask import Flask, jsonify, request, g, has_request_context
from flask_cors import CORS

class JSONFormatter(logging.Formatter):
    def format(self, record):
        trace_id = getattr(g, 'correlation_id', 'N/A') if has_request_context() else 'SYSTEM'
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "trace_id": trace_id
        }
        return json.dumps(log_record)

logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.setLevel(logging.INFO)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

db_lock = threading.Lock()

ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "password123")
VALID_TOKEN = os.getenv("APP_AUTH_TOKEN", "valid_admin_token")

accounts = {"user_1": 1000.0}
processed_transactions = set()
failed_login_attempts = {}

@app.before_request
def start_request():
    g.correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
    ip = request.remote_addr
    # THE FIX: Rate limit ONLY applies to /login
    if request.path == '/login' and failed_login_attempts.get(ip, 0) >= 5:
        logger.warning(f"Locked IP {ip} attempted access")
        return jsonify({"error": "Account locked"}), 429

@app.after_request
def end_request(response):
    response.headers['X-Correlation-ID'] = g.correlation_id
    return response

@app.route('/', methods=['GET'])
def index():
    return """<html><body><h2>Secure Portal</h2><input id='user' placeholder='User'/><input id='pass' type='password' placeholder='Pass'/><button id='btn'>Login</button><div id='msg'></div><script>document.getElementById('btn').onclick = async () => { const res = await fetch('/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username: document.getElementById('user').value, password: document.getElementById('pass').value})}); document.getElementById('msg').innerText = res.ok ? 'Token Received' : 'Access Denied'; }</script></body></html>"""

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    time.sleep(0.05) 
    if data.get("username") == "admin" and data.get("password") == ADMIN_PASS:
        failed_login_attempts[request.remote_addr] = 0
        logger.info("Successful login")
        return jsonify({"token": VALID_TOKEN}), 200
    failed_login_attempts[request.remote_addr] = failed_login_attempts.get(request.remote_addr, 0) + 1
    logger.warning("Failed login attempt")
    return jsonify({"error": "Unauthorized"}), 401

@app.route('/transfer', methods=['POST'])
def transfer():
    if request.headers.get("Authorization") != f"Bearer {VALID_TOKEN}":
        logger.warning("Unauthorized transfer attempt")
        return jsonify({"error": "Forbidden"}), 403

    idem_key = request.headers.get('X-Idempotency-Key')
    if not idem_key:
        return jsonify({"error": "Missing Idempotency-Key"}), 400
        
    amount = (request.get_json() or {}).get("amount", 0)

    with db_lock:
        if idem_key in processed_transactions:
            return jsonify({"error": "Duplicate", "status": "already_processed"}), 409
        if accounts["user_1"] >= amount:
            time.sleep(0.01) 
            accounts["user_1"] -= amount
            processed_transactions.add(idem_key)
            logger.info(f"Transfer successful: {amount}")
            return jsonify({"new_balance": accounts["user_1"]}), 200
    
    return jsonify({"error": "Insufficient funds"}), 400

@app.route('/api/resource', methods=['GET'])
def protected_resource():
    if request.headers.get("Authorization") != f"Bearer {VALID_TOKEN}":
        return jsonify({"error": "Forbidden"}), 403
    return jsonify({"data": "Secure Resource Access"}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, threaded=True)
