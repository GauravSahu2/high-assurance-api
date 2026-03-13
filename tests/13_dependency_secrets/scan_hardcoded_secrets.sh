#!/bin/bash
set -euo pipefail

echo "🔎 [Tier 13] Initiating Hardcoded Secrets Scan..."

TARGET_DIR="src/"

# Pattern 1: AWS Access Key ID
if grep -rE -q 'AKIA[0-9A-Z]{16}' "$TARGET_DIR" 2>/dev/null || false; then
    echo "🚨 [FATAL] AWS Access Key detected in source code!"
    exit 1
fi

# Pattern 2: RSA Private Keys
if grep -rE -q 'BEGIN RSA PRIVATE KEY' "$TARGET_DIR" 2>/dev/null || false; then
    echo "🚨 [FATAL] RSA Private Key detected in source code!"
    exit 1
fi

# Pattern 3: Live API Keys (e.g., Stripe or SendGrid formats)
if grep -rE -q '(sk_live|SG\.)[a-zA-Z0-9]+' "$TARGET_DIR" 2>/dev/null || false; then
    echo "🚨 [FATAL] High-entropy Live API Key detected!"
    exit 1
fi

echo "✅ [Tier 13] Secrets Scan Passed: 0 hardcoded AWS keys, private keys, or live API tokens found."
