#!/bin/bash
DATE=$(date +%Y-%m-%d)
BUNDLE_NAME="FDA_Evidence_Bundle_$DATE"

echo "=== Initiating FDA 21 CFR Part 11 Audit Packaging ==="

# 1. Run the Zero-Leak Check
bash tests/4_compliance/zero_leak_check.sh
if [ $? -ne 0 ]; then
    echo "ABORTING BUNDLE: Fix PII leaks before generating compliance report."
    exit 1
fi

# 2. Gather Evidence into a secure folder
echo "Gathering Test Evidence..."
mkdir -p audit_reports/$BUNDLE_NAME
cp -r logs/ audit_reports/$BUNDLE_NAME/
cp proofs/TransferLogic.tla audit_reports/$BUNDLE_NAME/
echo "k6 Load Test: FAILED p(95) latency threshold. Architecture scaling required." > audit_reports/$BUNDLE_NAME/performance_summary.txt

# 3. Create Immutable Archive
cd audit_reports
zip -r ${BUNDLE_NAME}.zip $BUNDLE_NAME > /dev/null

# 4. Generate SHA-256 Checksum for immutability
sha256sum ${BUNDLE_NAME}.zip > ${BUNDLE_NAME}.zip.sha256

echo "=== SUCCESS ==="
echo "Audit Bundle Created: audit_reports/${BUNDLE_NAME}.zip"
echo "Immutability Hash: $(cat ${BUNDLE_NAME}.zip.sha256)"
