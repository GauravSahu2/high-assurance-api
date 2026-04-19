import os
import json
import re
from flask import Blueprint, jsonify, send_file
from src.report_generator import generate_audit_statement

dashboard_bp = Blueprint("dashboard", __name__)

HSA_REPORTS_DIR = "hsa-reports"
AUDIT_REPORTS_DIR = "audit_reports"

def parse_markdown_table(file_path):
    """Simple parser for the complexity/hardware markdown tables."""
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, "r") as f:
        lines = f.readlines()
    
    table_data = []
    headers = []
    for line in lines:
        if "|" in line:
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            if not headers:
                if "---" not in line:
                    headers = cells
            elif "---" not in line:
                table_data.append(dict(zip(headers, cells)))
    return table_data

@dashboard_bp.route("/api/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    """Aggregates security scan results and test metadata."""
    stats = {
        "security": {
            "gitleaks": 0,
            "semgrep": 0,
            "trivy": 0
        },
        "tests": {
            "total": 0,
            "failures": 0,
            "time": 0
        }
    }
    
    # Parse Gitleaks
    gitleaks_path = os.path.join(HSA_REPORTS_DIR, "gitleaks.json")
    if os.path.exists(gitleaks_path):
        with open(gitleaks_path, "r") as f:
            data = json.load(f)
            stats["security"]["gitleaks"] = len(data) if data else 0

    # Parse Semgrep
    semgrep_path = os.path.join(HSA_REPORTS_DIR, "semgrep.json")
    if os.path.exists(semgrep_path):
        with open(semgrep_path, "r") as f:
            data = json.load(f)
            stats["security"]["semgrep"] = len(data.get("results", []))

    # Return summary
    return jsonify(stats)

@dashboard_bp.route("/api/dashboard/complexity", methods=["GET"])
def get_complexity_data():
    """Returns the time/space complexity matrix data."""
    matrix_path = "hardware_stats_matrix.md"
    return jsonify(parse_markdown_table(matrix_path))

@dashboard_bp.route("/api/dashboard/recommendations", methods=["GET"])
def get_recommendations():
    """Returns hardware/cloud recommendations."""
    matrix_path = "hardware_matrix.md"
    return jsonify(parse_markdown_table(matrix_path))

@dashboard_bp.route("/api/dashboard/download-report", methods=["GET"])
def download_report():
    """Generates and returns the executive technical report."""
    report_path = generate_audit_statement()
    return send_file(report_path, as_attachment=True)
