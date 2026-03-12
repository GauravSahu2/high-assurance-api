#!/bin/bash
# tests/7_edge_and_infrastructure/edge_security_checks.sh

TARGET_URL="https://google.com" # Replace with your actual API URL

echo "=== 1. Checking SSL/TLS Certificate Expiry ==="
# Pull the SSL certificate data from the server and extract the expiration date
EXPIRY_DATE=$(echo | openssl s_client -servername google.com -connect google.com:443 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
# Convert dates to seconds for mathematical comparison
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt 30 ]; then
    echo "FAIL: SSL Certificate expires in $DAYS_LEFT days! Action required immediately."
    exit 1
else
    echo "PASS: SSL Certificate is healthy. Expires in $DAYS_LEFT days."
fi

echo "=== 2. Testing WAF Rate Limiting (DDoS Simulation) ==="
# Send 50 rapid requests in a loop to see if the Edge server (Cloudflare/AWS WAF) blocks us
SUCCESS_COUNT=0
BLOCKED_COUNT=0

for i in {1..50}; do
    # -s: silent, -o /dev/null: hide output, -w: print HTTP status code
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" $TARGET_URL)
    if [ "$STATUS" -eq 429 ] || [ "$STATUS" -eq 403 ]; then
        ((BLOCKED_COUNT++))
    else
        ((SUCCESS_COUNT++))
    fi
done

# We EXPECT the WAF to block some requests (return 429 Too Many Requests)
if [ $BLOCKED_COUNT -gt 0 ]; then
    echo "PASS: WAF is active. Blocked $BLOCKED_COUNT rapid requests."
else
    echo "FAIL: WAF did not trigger! System is vulnerable to HTTP floods."
    # Note: If testing against Google, they might not block 50 requests. Against a strict API, they should.
fi
