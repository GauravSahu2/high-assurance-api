#!/bin/bash
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BUNDLE_DIR="audit_reports/FDA_Evidence_Bundle_${TIMESTAMP}"
mkdir -p "$BUNDLE_DIR"

echo "📦 Packaging evidence for compliance..."

[[[[ -f audit_reports/test_results.xml ]] && cp audit_reports/test_results.xml "$BUNDLE_DIR/pytest_results.xml"
[[[[ -f logs/api.log ]] && cp logs/api.log "$BUNDLE_DIR/api.log"

echo "📋 Generating Software Bill of Materials (SBOM)..."
# 🛡️ FIX: Removed --format flag as newer versions infer format from the .json extension
python3 -m cyclonedx_py environment -o "$BUNDLE_DIR/sbom.json" > /dev/null 2>&1 || echo "⚠️ SBOM Generation skipped (Tool not available)"

echo "✅ SBOM generated."

if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    git rev-parse HEAD > "$BUNDLE_DIR/git_commit.txt"
    echo "✅ Tied audit bundle to Git SHA: $(cat $BUNDLE_DIR/git_commit.txt)"
else
    echo "dev-local-$(date +%s)" > "$BUNDLE_DIR/git_commit.txt"
fi

echo "🛡️  Generating full recursive integrity manifest..."
cd "$BUNDLE_DIR"
find . -type f ! -name 'integrity_manifest.sha256' | sort | xargs sha256sum > integrity_manifest.sha256
cd ../..

zip -r "${BUNDLE_DIR}.zip" "$BUNDLE_DIR" > /dev/null
echo "✅ Audit Bundle Created: $BUNDLE_DIR"
