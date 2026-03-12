import pytest

def test_infrastructure_drift():
    # 1. The "Expected" state (What is written in our Terraform code)
    expected_firewall_ports = [443, 80]
    
    # 2. The "Actual" state (Simulating an API call to AWS to see what is currently running)
    # Oh no! Someone manually opened port 22 (SSH) in production!
    actual_firewall_ports = [443, 80, 22] 
    
    # 3. THE ASSERTION: The Cloud MUST perfectly match the Code.
    drift_detected = set(actual_firewall_ports) - set(expected_firewall_ports)
    
    # We purposely expect this to fail in our simulation to prove the monitor works!
    try:
        assert len(drift_detected) == 0, f"CRITICAL: Infrastructure Drift Detected! Unauthorized ports open: {drift_detected}"
        pytest.fail("The test failed to catch the drift!")
    except AssertionError as e:
        print(f"\n[SUCCESS] Drift Monitor active. Caught unauthorized manual changes: {drift_detected}")
