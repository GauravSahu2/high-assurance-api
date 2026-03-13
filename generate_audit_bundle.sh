#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BUNDLE_DIR="audit_reports/FDA_Evidence_Bundle_$TIMESTAMP"
mkdir -p "$BUNDLE_DIR"

echo "📦 Packaging evidence for compliance..."

# Core API Evidence
[ -f logs/api.log ] && cp logs/api.log "$BUNDLE_DIR/"
[ -f audit_reports/test_results.xml ] && cp audit_reports/test_results.xml "$BUNDLE_DIR/"

# Playwright Evidence (Screenshots/Traces)
if [ -d playwright-report ]; then
    echo "📸 Including Playwright E2E evidence..."
    cp -r playwright-report/ "$BUNDLE_DIR/"
fi

# Infrastructure & Compliance docs
cp docs/WARNING_SUPPRESSION.md "$BUNDLE_DIR/"

# FIX #1: SHA-256 Checksum with Recursive File Discovery
echo "🛡️  Generating full recursive manifest..."
cd "$BUNDLE_DIR"
# Finds all files, sorts for determinism, and hashes them
find . -type f ! -name 'manifests.sha256' | sort | xargs sha256sum > manifests.sha256
cd ../..

# Zip the bundle
zip -r "$BUNDLE_DIR.zip" "$BUNDLE_DIR" > /dev/null
echo "✅ Audit Bundle Created: $BUNDLE_DIR"
