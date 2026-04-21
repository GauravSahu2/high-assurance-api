#!/bin/bash
set -euo pipefail

echo "🔎 [Tier 4] Initiating PII Zero-Leak Scan on runtime logs..."

LOG_FILE="logs/api.log"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "⚠️  Log file not found at $LOG_FILE. Ensure the API is running."
    exit 1
fi

# Pattern 1: Fake SSN or Credit Card Regex
if grep -E -q '([0-9]{3}-[0-9]{2}-[0-9]{4}|[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4})' "$LOG_FILE" 2>/dev/null || false; then
    echo "🚨 [FATAL] PII Leak detected in logs! (SSN or Credit Card format)"
    exit 1
fi

echo "✅ [Tier 4] Compliance Verified: 0 PII leaks detected in runtime logs."
