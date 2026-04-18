import json
import os
import sys

REPORTS_DIR = "hsa-reports"

def print_header(title, color_code="\033[96m"):
    print(f"\n{color_code}{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\033[0m")

def parse_gitleaks():
    path = os.path.join(REPORTS_DIR, "gitleaks.json")
    print_header("🔐 SECRETS SCAN (GITLEAKS)", "\033[93m")
    if not os.path.exists(path):
        print("  [!] No Gitleaks report found.")
        return

    with open(path, 'r') as f:
        try:
            data = json.load(f)
            if not data:
                print("  \033[92m[✅ CLEAN] 0 Hardcoded Secrets Found.\033[0m")
            else:
                print(f"  \033[91m[🚨 ALERT] {len(data)} Secrets Detected!\033[0m")
                for finding in data[:5]:
                    print(f"    - File: {finding.get('File')} | Rule: {finding.get('RuleID')}")
        except:
            print("  [!] Error reading Gitleaks JSON.")

def parse_semgrep():
    path = os.path.join(REPORTS_DIR, "semgrep.json")
    print_header("🧠 SAST VULNERABILITIES (SEMGREP)", "\033[94m")
    if not os.path.exists(path):
        print("  [!] No Semgrep report found.")
        return

    with open(path, 'r') as f:
        try:
            data = json.load(f)
            results = data.get("results", [])
            if not results:
                print("  \033[92m[✅ CLEAN] 0 Static Vulnerabilities Found.\033[0m")
            else:
                print(f"  \033[91m[🚨 ALERT] {len(results)} Code Vulnerabilities Detected!\033[0m")
                for r in results[:5]:
                    print(f"    - [{r.get('extra', {}).get('severity', 'WARN')}] {r.get('path')}: {r.get('check_id')}")
        except:
            print("  [!] Error reading Semgrep JSON.")

def parse_trivy():
    path = os.path.join(REPORTS_DIR, "trivy.json")
    print_header("📦 DEPENDENCY CVEs (TRIVY)", "\033[95m")
    if not os.path.exists(path):
        print("  [!] No Trivy report found.")
        return

    with open(path, 'r') as f:
        try:
            data = json.load(f)
            results = data.get("Results", [])
            cve_count = sum(len(target.get("Vulnerabilities", [])) for target in results)
            
            if cve_count == 0:
                print("  \033[92m[✅ CLEAN] 0 Known CVEs in Dependencies.\033[0m")
            else:
                print(f"  \033[91m[🚨 ALERT] {cve_count} Vulnerable Packages Detected!\033[0m")
                for target in results:
                    for vuln in target.get("Vulnerabilities", [])[:5]:
                        print(f"    - {vuln.get('PkgName')} ({vuln.get('InstalledVersion')}) -> {vuln.get('VulnerabilityID')} [{vuln.get('Severity')}]")
        except:
            print("  [!] Error reading Trivy JSON.")

if __name__ == "__main__":
    if not os.path.exists(REPORTS_DIR):
        print(f"\033[91m[!] {REPORTS_DIR} folder not found. Run 'hsa scan .' first.\033[0m")
        sys.exit(1)
        
    print("\n\033[1m📊 HSA UNIVERSAL SECURITY PROFILE\033[0m")
    parse_gitleaks()
    parse_semgrep()
    parse_trivy()
    print("\n")
