import pytest
from src.report_generator import generate_audit_statement
from src.routes.dashboard_routes import parse_markdown_table

def test_dashboard_stats_endpoint(client, auth_header):
    """Test that the dashboard stats endpoint returns the correct structure."""
    response = client.get("/api/dashboard/stats", headers=auth_header)
    assert response.status_code == 200
    data = response.json
    assert "security" in data
    assert "tests" in data

def test_dashboard_complexity_endpoint(client, auth_header):
    """Test that the complexity endpoint returns scaling matrix data."""
    response = client.get("/api/dashboard/complexity", headers=auth_header)
    assert response.status_code == 200
    data = response.json
    assert isinstance(data, list)
    assert len(data) > 0
    assert "Concurrent User Load" in data[0]

def test_dashboard_report_download(client, auth_header):
    """Test that the report download endpoint returns a markdown file."""
    response = client.get("/api/dashboard/download-report", headers=auth_header)
    assert response.status_code == 200
    assert "text/markdown" in response.headers["Content-Type"]
    assert b"Executive Technical Audit Statement" in response.data

def test_dashboard_recommendations_endpoint(client, auth_header):
    """Test the recommendations endpoint and missing markdown file coverage."""
    response = client.get("/api/dashboard/recommendations", headers=auth_header)
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_parse_markdown_table_missing_file():
    """Test that missing table files return an empty list."""
    assert parse_markdown_table("does_not_exist_in_reality.md") == []

def test_report_generator_logic():
    """Unit test for the internal report generator logic."""
    stats = {
        "security": {"gitleaks": 0, "trivy": 0, "semgrep": 0},
        "test_health": {"tests": 100, "failures": 0}
    }
    report_path = generate_audit_statement(stats)
    with open(report_path, "r") as f:
        report_content = f.read()
    assert "TOTAL TIERS VERIFIED: 32" in report_content
    assert "TRUST SCORE: 98.4%" in report_content
