import os
from datetime import datetime

import requests


def fetch_sonar_metrics():
    sonar_token = os.environ.get("SONAR_TOKEN")
    project_key = "GauravSahu2_high-assurance-api"

    if not sonar_token:
        print("SONAR_TOKEN not found. Skipping report generation.")
        return

    url = "https://sonarcloud.io/api/measures/component"
    params = {
        "component": project_key,
        "metricKeys": (
            "alert_status,bugs,vulnerabilities,code_smells,coverage,"
            "duplicated_lines_density,sqale_index,reliability_rating,"
            "security_rating,sqale_rating"
        ),
    }

    try:
        response = requests.get(url, params=params, auth=(sonar_token, ""), timeout=30)
        response.raise_for_status()
        data = response.json()

        measures = {m["metric"]: m["value"] for m in data["component"]["measures"]}

        report_path = "sonar_report.md"
        with open(report_path, "w") as f:
            f.write("# 🛡️ SonarCloud Quality Audit Report\n")
            f.write(f"**Date Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Project**: `{project_key}`\n\n")

            status = measures.get("alert_status", "UNKNOWN")
            status_emoji = "✅ PASS" if status == "OK" else "❌ FAIL"
            f.write(f"## 🏁 Quality Gate Status: {status_emoji} ({status})\n\n")

            f.write("### 📊 Key Metrics\n")
            f.write("| Metric | Value | Rating |\n")
            f.write("| :--- | :--- | :--- |\n")
            f.write(f"| 🐛 **Bugs** | {measures.get('bugs', '0')} | {measures.get('reliability_rating', 'N/A')} |\n")
            f.write(
                f"| 🔓 **Vulnerabilities** | {measures.get('vulnerabilities', '0')} | "
                f"{measures.get('security_rating', 'N/A')} |\n"
            )
            f.write(
                f"| ☣️ **Code Smells** | {measures.get('code_smells', '0')} | "
                f"{measures.get('sqale_rating', 'N/A')} |\n"
            )
            f.write(f"| 🧪 **Test Coverage** | {measures.get('coverage', '0')}% | - |\n")
            f.write(f"| 📋 **Duplications** | {measures.get('duplicated_lines_density', '0')}% | - |\n")
            f.write(f"| ⏱️ **Technical Debt** | {measures.get('sqale_index', '0')} min | - |\n\n")

            f.write("## 👑 Compliance Attestation\n")
            f.write(
                "This project adheres to high-assurance standards. "
                "All critical and high issues must be resolved before deployment.\n\n"
            )
            f.write("---\n")
            f.write("*Report generated automatically by HSA Pipeline.*\n")

        print(f"✅ SonarCloud report generated: {report_path}")

    except Exception as e:
        print(f"❌ Failed to fetch SonarCloud metrics: {e}")


if __name__ == "__main__":
    fetch_sonar_metrics()
