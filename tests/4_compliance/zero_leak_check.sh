#!/bin/bash
echo "Running Zero-Leak PII Scan on all system logs..."

# Regex search for a 16-digit credit card pattern
if grep -rE -q "\b[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}\b" logs/; then
    echo "CRITICAL FAIL: PII (Credit Card Pattern) DETECTED IN LOGS!"
    exit 1
else
    echo "PASS: No PII leaked in logs. Zero-Trust verified."
    exit 0
fi
