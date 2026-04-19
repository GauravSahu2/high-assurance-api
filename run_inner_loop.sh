#!/bin/bash
set -euo pipefail

echo "⚡ INITIATING HIGH-ASSURANCE 32-TIER INNER LOOP (WITH BENCHMARKS)..."

# 1. HARD ENVIRONMENT RESET
echo "🧹 Clearing stale processes & state..."
fuser -k 5000/tcp > /dev/null 2>&1 || true
rm -f server_inner.log

# 2. Parallel Functional Tests (THE COVERAGE GATE)
# This stage enforces the 100% coverage requirement across 16 workers
echo "🧪 Running parallel functional tests (16 Workers)..."
PYTHONPATH=.:src TEST_MODE=true pytest tests/ -p no:warnings --cov=src -rsno --cov-report=term-missing -n auto --ignore-glob='*test_api_performance.py*'

# 3. Boot background server
echo "🚀 Booting background server..."
PYTHONPATH=.:src TEST_MODE=true JWT_SECRET="super-secure-dev-secret-key-12345678901234567890123448byteslong" gunicorn --bind 0.0.0.0:5000 --workers 1 "main:app" > server_inner.log 2>&1 &
    sleep 3
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

# Wait for bind
for i in {1..5}; do
    if curl -sf http://localhost:5000/health > /dev/null 2>&1; then break; fi
    sleep 0.5
done

# 4. Authorize Fuzzer
echo "🎟️ Authorizing Fuzzer..."
TOKEN=$(curl -s -X POST http://localhost:5000/login -H "Content-Type: application/json" -d '{"username":"admin", "password":"password123"}' | grep -o '"token":"[^"]*' | cut -d'"' -f4 || echo "")

if [ -z "$TOKEN" ]; then
    echo "❌ FAILED to authorize fuzzer."
    exit 1
fi

# 5. Clean DAST Fuzzing
echo "🔍 Running Schemathesis Fuzzing..."
schemathesis run openapi.yaml --url http://localhost:5000 --workers 1 -H "Authorization: Bearer $TOKEN" --checks not_a_server_error

# 6. Sequential Performance Gate (THE LATENCY GATE)
# We add --no-cov here to prevent the "58% coverage" failure on this benchmark-only run
echo -e "\n📊 VERIFYING PERFORMANCE METRICS (No-Noise Sequential)..."
PYTHONPATH=.:src TEST_MODE=true pytest tests/14_algorithmic_complexity/test_api_performance.py -p no:warnings --benchmark-only --no-cov

echo "✅ INNER LOOP COMPLETE. Logic (100%), Security (Passed), and Performance verified."
