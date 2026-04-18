#!/usr/bin/env python3
"""
Exposure Audit Scanner — Pre-Deploy LeakIX Defense Layer
═══════════════════════════════════════════════════════════════════════════════
Scans the codebase for patterns that would trigger LeakIX, Shodan, or Censys
detections if deployed to a public-facing environment.

This runs BEFORE deployment so you catch exposure risks in CI, not after an
attacker finds them.

Usage:
    python scripts/exposure_audit.py                    # default: text output
    python scripts/exposure_audit.py --format github    # GitHub Actions summary
    python scripts/exposure_audit.py --fail-on critical # exit 1 on criticals
    python scripts/exposure_audit.py --fail-on warning  # exit 1 on warnings+

What it catches:
    • Debug/test endpoints exposed in production code
    • Default or hardcoded credentials
    • Exposed internal service ports (Redis, Postgres, Elasticsearch)
    • Missing security headers that aid fingerprinting
    • Open CORS wildcards
    • Sensitive files that shouldn't be served (.env, .git, etc.)
    • Server version disclosure in responses
    • Exposed metrics/health endpoints without auth
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Optional


class Severity(IntEnum):
    INFO = 0
    WARNING = 1
    CRITICAL = 2


@dataclass
class Finding:
    severity: Severity
    category: str
    title: str
    description: str
    file: Optional[str] = None
    line: Optional[int] = None
    recommendation: str = ""


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)

    def add(self, finding: Finding):
        self.findings.append(finding)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)


# ── Scanner Functions ──────────────────────────────────────────────────────────

def scan_debug_endpoints(root: Path, report: AuditReport):
    """Detect debug/test routes that should not exist in production."""
    dangerous_patterns = [
        (r'@app\.route\(["\']\/debug', "Debug endpoint exposed"),
        (r'@app\.route\(["\']\/test\/', "Test-only endpoint found"),
        (r'@app\.route\(["\']\/admin', "Admin panel endpoint (verify auth)"),
        (r'@app\.route\(["\']\/phpinfo', "PHP info endpoint exposure"),
        (r'@app\.route\(["\']\/\.env', "Direct .env route exposure"),
        (r'@app\.route\(["\']\/console', "Console/shell endpoint exposure"),
        (r'app\.debug\s*=\s*True', "Flask debug mode enabled"),
        (r'DEBUG\s*=\s*True', "Debug flag set to True"),
    ]

    # Test-gated endpoints are acceptable — only flag ungated ones
    for py_file in root.rglob("src/**/*.py"):
        try:
            content = py_file.read_text(errors="ignore")
            lines = content.splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            for pattern, desc in dangerous_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Check if it's gated behind TEST_MODE (look before AND after)
                    context_before = "\n".join(lines[max(0, i - 6):i - 1])
                    context_after = "\n".join(lines[i - 1:min(i + 10, len(lines))])
                    context = context_before + "\n" + context_after
                    if "TEST_MODE" in context or 'environ.get("TEST_MODE")' in line:
                        report.add(Finding(
                            severity=Severity.INFO,
                            category="Debug Endpoints",
                            title=f"{desc} (TEST_MODE gated — safe)",
                            description=f"Found `{pattern}` but it's properly gated behind TEST_MODE.",
                            file=str(py_file.relative_to(root)),
                            line=i,
                            recommendation="No action needed — already gated."
                        ))
                    else:
                        report.add(Finding(
                            severity=Severity.CRITICAL,
                            category="Debug Endpoints",
                            title=desc,
                            description=f"Detected pattern `{pattern}` without environment gating.",
                            file=str(py_file.relative_to(root)),
                            line=i,
                            recommendation="Gate behind TEST_MODE or remove before production deployment."
                        ))


def scan_default_credentials(root: Path, report: AuditReport):
    """Detect hardcoded default passwords or API keys."""
    cred_patterns = [
        (r'password\s*[=:]\s*["\'](?:password|admin|root|test|123|default)', "Hardcoded default password"),
        (r'api[_-]?key\s*[=:]\s*["\'][a-zA-Z0-9]{20,}', "Hardcoded API key"),
        (r'secret[_-]?key\s*[=:]\s*["\'][^"\']{10,}', "Hardcoded secret key"),
        (r'POSTGRES_PASSWORD:\s*password', "Default Postgres password in compose"),
        (r'REDIS_PASSWORD:\s*["\']?password', "Default Redis password"),
    ]

    scan_files = list(root.rglob("*.py")) + list(root.rglob("*.yml")) + list(root.rglob("*.yaml"))
    scan_files += list(root.rglob("*.env")) + list(root.rglob("*.env.example"))

    for f in scan_files:
        if any(skip in str(f) for skip in ["venv/", "node_modules/", ".git/", "__pycache__"]):
            continue
        try:
            content = f.read_text(errors="ignore")
            lines = content.splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            for pattern, desc in cred_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Default creds in test fixtures or docker-compose for local dev are warnings, not criticals
                    is_local = any(x in str(f) for x in ["test", "docker-compose", ".env.example", "conftest"])
                    report.add(Finding(
                        severity=Severity.WARNING if is_local else Severity.CRITICAL,
                        category="Default Credentials",
                        title=desc,
                        description=f"Pattern `{pattern}` matched in {f.relative_to(root)}",
                        file=str(f.relative_to(root)),
                        line=i,
                        recommendation="Use secrets manager (AWS SM, Vault) or environment variables in production."
                    ))


def scan_exposed_ports(root: Path, report: AuditReport):
    """Detect services binding to 0.0.0.0 or exposing internal ports."""
    dangerous_binds = [
        (r'0\.0\.0\.0:(?:6379|26379)', "Redis exposed on all interfaces"),
        (r'0\.0\.0\.0:(?:5432|3306)', "Database exposed on all interfaces"),
        (r'0\.0\.0\.0:(?:9200|9300)', "Elasticsearch exposed on all interfaces"),
        (r'0\.0\.0\.0:(?:27017|27018)', "MongoDB exposed on all interfaces"),
        (r'0\.0\.0\.0:(?:2375|2376)', "Docker daemon exposed on all interfaces"),
        (r'0\.0\.0\.0:(?:8500|8600)', "Consul exposed on all interfaces"),
        (r'0\.0\.0\.0:(?:2379|2380)', "etcd exposed on all interfaces"),
    ]

    for f in list(root.rglob("*.yml")) + list(root.rglob("*.yaml")) + list(root.rglob("*.py")):
        if any(skip in str(f) for skip in ["venv/", "node_modules/", ".git/"]):
            continue
        try:
            content = f.read_text(errors="ignore")
            lines = content.splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            for pattern, desc in dangerous_binds:
                if re.search(pattern, line):
                    report.add(Finding(
                        severity=Severity.CRITICAL,
                        category="Exposed Ports",
                        title=desc,
                        description=f"Service binding to all interfaces detected in {f.relative_to(root)}",
                        file=str(f.relative_to(root)),
                        line=i,
                        recommendation="Bind to 127.0.0.1 or use network policies to restrict access."
                    ))


def scan_security_headers(root: Path, report: AuditReport):
    """Check if the application sets proper security headers."""
    required_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "X-XSS-Protection",
    ]

    # Check security.py or main.py for header configuration
    header_files = list(root.rglob("src/security.py")) + list(root.rglob("src/main.py"))
    all_content = ""
    for f in header_files:
        try:
            all_content += f.read_text(errors="ignore")
        except Exception:
            continue

    for header in required_headers:
        if header not in all_content:
            report.add(Finding(
                severity=Severity.WARNING,
                category="Security Headers",
                title=f"Missing {header} header",
                description=f"The `{header}` header was not found in security configuration.",
                recommendation=f"Add `{header}` to your response headers in security.py."
            ))
        else:
            report.add(Finding(
                severity=Severity.INFO,
                category="Security Headers",
                title=f"{header} configured ✓",
                description=f"Header `{header}` is properly set.",
            ))


def scan_cors_configuration(root: Path, report: AuditReport):
    """Detect overly permissive CORS configurations."""
    for py_file in root.rglob("src/**/*.py"):
        try:
            content = py_file.read_text(errors="ignore")
            lines = content.splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            # Wildcard CORS
            if re.search(r'origins\s*=\s*["\']\*["\']', line) or re.search(r"CORS\(.*\*", line):
                report.add(Finding(
                    severity=Severity.CRITICAL,
                    category="CORS Configuration",
                    title="Wildcard CORS origin detected",
                    description="CORS is configured to allow all origins (*), which allows any website to make authenticated requests.",
                    file=str(py_file.relative_to(root)),
                    line=i,
                    recommendation="Restrict CORS origins to specific trusted domains."
                ))
            # Explicit allowed origins — good
            elif "ALLOWED_ORIGINS" in line or "origins=" in line:
                report.add(Finding(
                    severity=Severity.INFO,
                    category="CORS Configuration",
                    title="CORS origins explicitly configured ✓",
                    description="CORS is restricted to specific origins.",
                    file=str(py_file.relative_to(root)),
                    line=i,
                ))


def scan_sensitive_files(root: Path, report: AuditReport):
    """Check for sensitive files that should be in .gitignore."""
    sensitive_patterns = [
        (".env", "Environment file with potential secrets"),
        (".pem", "Private key file"),
        (".key", "Private key file"),
        (".p12", "PKCS12 certificate bundle"),
        ("id_rsa", "SSH private key"),
        ("credentials.json", "Cloud credentials file"),
        ("service-account.json", "GCP service account key"),
    ]

    gitignore_content = ""
    gitignore_path = root / ".gitignore"
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text(errors="ignore")

    for pattern, desc in sensitive_patterns:
        matches = list(root.rglob(f"*{pattern}"))
        matches = [m for m in matches if not any(skip in str(m) for skip in ["venv/", "node_modules/", ".git/"])]

        for match in matches:
            rel = match.relative_to(root)
            is_ignored = pattern in gitignore_content or str(rel) in gitignore_content
            if match.suffix == ".env" and str(rel) == ".env.example":
                continue  # .env.example is fine

            report.add(Finding(
                severity=Severity.INFO if is_ignored else Severity.WARNING,
                category="Sensitive Files",
                title=f"{desc}: {rel}",
                description=f"Found `{rel}` — {'already in .gitignore ✓' if is_ignored else 'NOT in .gitignore!'}",
                file=str(rel),
                recommendation="Ensure this file is in .gitignore and never committed to version control." if not is_ignored else ""
            ))


def scan_version_disclosure(root: Path, report: AuditReport):
    """Check if the app discloses server version information."""
    for py_file in root.rglob("src/**/*.py"):
        try:
            content = py_file.read_text(errors="ignore")
            lines = content.splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            if re.search(r'["\']Server["\'].*["\'].*\d+\.\d+', line):
                report.add(Finding(
                    severity=Severity.WARNING,
                    category="Version Disclosure",
                    title="Server version disclosed in response headers",
                    description="Exposing server version helps attackers target known CVEs.",
                    file=str(py_file.relative_to(root)),
                    line=i,
                    recommendation="Remove or genericize Server header value."
                ))

    # Check if X-Powered-By is being suppressed
    security_files = list(root.rglob("src/security.py"))
    for f in security_files:
        content = f.read_text(errors="ignore")
        if "X-Powered-By" not in content:
            report.add(Finding(
                severity=Severity.INFO,
                category="Version Disclosure",
                title="X-Powered-By header not explicitly removed",
                description="Flask doesn't set X-Powered-By by default, but proxy layers might.",
                recommendation="Consider adding `response.headers.pop('X-Powered-By', None)` to be safe."
            ))


def scan_unprotected_endpoints(root: Path, report: AuditReport):
    """Detect endpoints that might expose internal data without auth."""
    risky_endpoints = [
        (r'@app\.route\(["\']\/metrics', "Prometheus metrics endpoint"),
        (r'@app\.route\(["\']\/health', "Health check endpoint"),
        (r'@app\.route\(["\']\/status', "Status endpoint"),
        (r'@app\.route\(["\']\/info', "Info endpoint"),
        (r'@app\.route\(["\']\/swagger', "Swagger UI endpoint"),
        (r'@app\.route\(["\']\/docs', "Documentation endpoint"),
        (r'@app\.route\(["\']\/openapi', "OpenAPI spec endpoint"),
    ]

    for py_file in root.rglob("src/**/*.py"):
        try:
            content = py_file.read_text(errors="ignore")
            lines = content.splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines, 1):
            for pattern, desc in risky_endpoints:
                if re.search(pattern, line, re.IGNORECASE):
                    # Check next few lines for auth checks
                    context = "\n".join(lines[i:min(i + 5, len(lines))])
                    has_auth = any(kw in context for kw in ["verify_jwt", "Authorization", "authenticate", "login_required"])

                    report.add(Finding(
                        severity=Severity.INFO if has_auth else Severity.WARNING,
                        category="Unprotected Endpoints",
                        title=f"{desc} {'(auth gated ✓)' if has_auth else '(NO AUTH)'}",
                        description=f"Endpoint at line {i} {'requires authentication' if has_auth else 'is publicly accessible — may leak infrastructure details to LeakIX scanners'}",
                        file=str(py_file.relative_to(root)),
                        line=i,
                        recommendation="" if has_auth else "Consider rate-limiting or adding basic auth to prevent enumeration."
                    ))


# ── Output Formatters ──────────────────────────────────────────────────────────

def format_text(report: AuditReport) -> str:
    """Plain text output."""
    lines = []
    lines.append("=" * 72)
    lines.append("  EXPOSURE AUDIT REPORT — LeakIX Pre-Deploy Defense Layer")
    lines.append("=" * 72)
    lines.append("")

    for severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
        findings = [f for f in report.findings if f.severity == severity]
        if not findings:
            continue
        label = {Severity.CRITICAL: "🚨 CRITICAL", Severity.WARNING: "⚠️  WARNING", Severity.INFO: "ℹ️  INFO"}[severity]
        lines.append(f"\n{'─' * 72}")
        lines.append(f"  {label} ({len(findings)} finding{'s' if len(findings) != 1 else ''})")
        lines.append(f"{'─' * 72}")

        for f in findings:
            loc = f"  📄 {f.file}:{f.line}" if f.file and f.line else ""
            lines.append(f"\n  [{f.category}] {f.title}")
            lines.append(f"  {f.description}")
            if loc:
                lines.append(loc)
            if f.recommendation:
                lines.append(f"  💡 {f.recommendation}")

    lines.append(f"\n{'=' * 72}")
    lines.append(f"  SUMMARY: {report.critical_count} critical, {report.warning_count} warnings, {report.info_count} info")
    lines.append(f"{'=' * 72}")
    return "\n".join(lines)


def format_github(report: AuditReport) -> str:
    """GitHub Actions compatible output with annotations."""
    lines = []

    # Emit GitHub Actions annotations for criticals and warnings
    for f in report.findings:
        if f.severity == Severity.CRITICAL and f.file and f.line:
            lines.append(f"::error file={f.file},line={f.line}::[{f.category}] {f.title}: {f.description}")
        elif f.severity == Severity.WARNING and f.file and f.line:
            lines.append(f"::warning file={f.file},line={f.line}::[{f.category}] {f.title}: {f.description}")

    # Also output full text report
    lines.append(format_text(report))
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pre-deploy exposure audit scanner")
    parser.add_argument("--root", default=".", help="Project root directory to scan")
    parser.add_argument("--format", choices=["text", "github"], default="text", help="Output format")
    parser.add_argument("--fail-on", choices=["critical", "warning", "none"], default="none",
                        help="Exit with code 1 if findings at this severity or above are detected")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = AuditReport()

    # Run all scanners
    scan_debug_endpoints(root, report)
    scan_default_credentials(root, report)
    scan_exposed_ports(root, report)
    scan_security_headers(root, report)
    scan_cors_configuration(root, report)
    scan_sensitive_files(root, report)
    scan_version_disclosure(root, report)
    scan_unprotected_endpoints(root, report)

    # Output
    if args.format == "github":
        print(format_github(report))
    else:
        print(format_text(report))

    # Exit code based on fail-on threshold
    if args.fail_on == "critical" and report.critical_count > 0:
        sys.exit(1)
    elif args.fail_on == "warning" and (report.critical_count > 0 or report.warning_count > 0):
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
