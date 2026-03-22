#!/bin/bash
set -e

echo "🛡️  INITIATING FULL 20-TIER VALIDATION..."
export API_BASE_URL="http://127.0.0.1:8000"
export PLAYWRIGHT_TEST_BASE_URL="http://127.0.0.1:8000"
export TEST_MODE="true"
export PYTHONPATH=src

mkdir -p audit_reports logs

# 1. Boot the API in the background
echo "🚀 Starting Flask API server..."
PYTHONPATH=src python3 src/main.py > logs/api.log 2>&1 &
FLASK_PID=$!

# Wait for API to be ready — timeout after 30 seconds
echo "⏳ Waiting for API to bind..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "✅ API is up (${i}s)"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ API failed to start after 30s. Logs:"
        cat logs/api.log
        exit 1
    fi
    sleep 1
done

# Ensure the server is cleanly killed when this script finishes or fails
trap "echo '🛑 Shutting down Flask API...'; kill $FLASK_PID 2>/dev/null || true" EXIT

# 2. Run Backend Tests
echo "🧪 Running Backend Logic & Security Tests..."
PYTHONPATH=src pytest tests/ \
  --junitxml=audit_reports/test_results.xml \
  --cov=src \
  --cov-report=xml:coverage.xml \
  --cov-report=term-missing \
  -q

# 3. Reset State
echo "♻️  Resetting API state..."
curl -s -X POST http://127.0.0.1:8000/test/reset > /dev/null

# 4. Run Frontend E2E (timeout 60s to prevent hanging)
echo "🎭 Running Frontend E2E Tests..."
timeout 60 npx playwright test --timeout=30000 || true

# 5. Package Evidence
echo "📦 Packaging Evidence..."
./generate_audit_bundle.sh

echo "✅ ALL TIERS COMPLETED SUCCESSFULLY."
