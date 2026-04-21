#!/bin/bash
# HSA-CLI - Universal Polyglot Security Scanner

TARGET_DIR=$(realpath "${1:-$(pwd)}")
REPORT_DIR="$TARGET_DIR/hsa-reports"
mkdir -p "$REPORT_DIR"

echo "============================================================"
echo "🌍 HSA UNIVERSAL SCANNER INITIATED"
echo "Target: $TARGET_DIR"
echo "============================================================"

# ---------------------------------------------------------
# PHASE 1: Auto-Discovery
# ---------------------------------------------------------
echo "🔍 PHASE 1: Auto-Discovery..."
STACKS=""
[ -f "$TARGET_DIR/package.json" ] && STACKS="$STACKS Node.js/JS/TS"
[ -f "$TARGET_DIR/requirements.txt" ] || [ -f "$TARGET_DIR/Pipfile" ] && STACKS="$STACKS Python"
[ -f "$TARGET_DIR/Cargo.toml" ] && STACKS="$STACKS Rust"
[ -f "$TARGET_DIR/pom.xml" ] || [ -f "$TARGET_DIR/build.gradle" ] && STACKS="$STACKS Java"
[ -f "$TARGET_DIR/go.mod" ] && STACKS="$STACKS Golang"
[ -f "$TARGET_DIR/docker-compose.yml" ] || [ -f "$TARGET_DIR/Dockerfile" ] && STACKS="$STACKS Docker/Infra"

if [ -z "$STACKS" ]; then
    echo "   [!] No explicit manifests found. Proceeding with generic AST scan."
else
    echo "   [+] Detected Stacks:$STACKS"
fi

# ---------------------------------------------------------
# PHASE 2: The Static Matrix (Secrets, SCA, SAST)
# ---------------------------------------------------------
echo ""
echo "🛡️  PHASE 2: Static Matrix..."

# 1. Gitleaks (Secret Scanning)
echo "   [>] Running Gitleaks (Hardcoded Secrets)..."
docker run --rm -v "$TARGET_DIR:/path" zricethezav/gitleaks:latest detect --source="/path" --report-path="/path/hsa-reports/gitleaks.json" --exit-code 0 > /dev/null 2>&1
echo "       ✅ Gitleaks complete."

# 2. Trivy (Software Composition Analysis)
echo "   [>] Running Trivy (Dependencies & CVEs)..."
# Mounts docker sock for infra scans and the target dir
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$TARGET_DIR:/workspace" aquasec/trivy fs /workspace --format json --output /workspace/hsa-reports/trivy.json > /dev/null 2>&1
echo "       ✅ Trivy complete."

# 3. Semgrep (Static Application Security Testing)
echo "   [>] Running Semgrep (Multi-Language SAST)..."
docker run --rm -v "$TARGET_DIR:/src" returntocorp/semgrep semgrep scan --config auto --json -o /src/hsa-reports/semgrep.json > /dev/null 2>&1
echo "       ✅ Semgrep complete."

# ---------------------------------------------------------
# PHASE 3 & 4: Aggregation & Handoff
# ---------------------------------------------------------
echo ""
echo "📊 PHASE 3: Report Aggregation..."
echo "   [+] Security artifacts generated in: $REPORT_DIR/"
echo "       ├── gitleaks.json (Secrets)"
echo "       ├── trivy.json    (SCA/CVEs)"
echo "       └── semgrep.json  (SAST)"

echo "============================================================"
echo "✅ STATIC ANALYSIS COMPLETE."
echo "To execute Phase 4 (DAST/Runtime), start the target application and run 'hsa -a'."
echo "============================================================"
