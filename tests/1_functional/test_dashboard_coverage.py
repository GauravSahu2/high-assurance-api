import json
import os


def test_dashboard_stats_report_parsing(client):
    """Ensure dashboard stats correctly parse security reports for 100% coverage."""
    report_dir = "hsa-reports"
    os.makedirs(report_dir, exist_ok=True)
    
    gitleaks_path = os.path.join(report_dir, "gitleaks.json")
    semgrep_path = os.path.join(report_dir, "semgrep.json")
    
    with open(gitleaks_path, "w") as f:
        json.dump([{"file": "test.py", "offense": "secret"}], f)
        
    with open(semgrep_path, "w") as f:
        json.dump({"results": [{"id": "test-rule"}]}, f)
        
    try:
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert data["security"]["gitleaks"] == 1
        assert data["security"]["semgrep"] == 1
    finally:
        if os.path.exists(gitleaks_path):
            os.remove(gitleaks_path)
        if os.path.exists(semgrep_path):
            os.remove(semgrep_path)
