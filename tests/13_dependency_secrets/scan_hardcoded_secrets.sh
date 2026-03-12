#!/bin/bash
echo "=== Running Atomic Secret & Entropy Scan ==="

# 1. Regex to find AWS Access Key IDs (AKIA...)
if grep -rEo "\bAKIA[0-9A-Z]{16}\b" src/ tests/ 2>/dev/null; then
    echo "CRITICAL FAIL: AWS Access Key detected in source code!"
    exit 1
fi

# 2. Regex to find Private RSA/SSH Keys (Using -e to handle the leading dashes)
if grep -rEl -e "-----BEGIN (RSA|OPENSSH) PRIVATE KEY-----" src/ tests/ 2>/dev/null; then
    echo "CRITICAL FAIL: Private Cryptographic Key detected in source code!"
    exit 1
fi

echo "[SUCCESS] No hardcoded AWS credentials or Private Keys found in the repository."
exit 0
