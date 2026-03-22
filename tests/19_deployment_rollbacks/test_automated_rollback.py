def simulate_blue_green_deployment(new_version_health_status):
    # The router starts by pointing 100% of traffic to the old, stable version
    traffic_routing = {"v1_stable": 100, "v2_new": 0}

    # Deployment starts: Shift 10% of traffic to the new version (Canary Release)
    traffic_routing = {"v1_stable": 90, "v2_new": 10}

    # Evaluate the health of the new version
    if new_version_health_status == "500_INTERNAL_SERVER_ERROR":
        # ATOMIC RULE: If the canary throws 500s, instantly roll back to v1!
        traffic_routing = {"v1_stable": 100, "v2_new": 0}
        return "ROLLED_BACK", traffic_routing

    # If healthy, shift 100% of traffic
    traffic_routing = {"v1_stable": 0, "v2_new": 100}
    return "DEPLOY_SUCCESS", traffic_routing


def test_automated_rollback():
    # Simulate a toxic deployment that crashes
    status, final_routing = simulate_blue_green_deployment("500_INTERNAL_SERVER_ERROR")

    # THE ASSERTION: The system must have reverted 100% of traffic back to the stable version
    assert status == "ROLLED_BACK"
    assert final_routing["v1_stable"] == 100, "CRITICAL: System left users stranded on a broken deployment!"
    print("\n[SUCCESS] Automated Rollback verified. Toxic deployments are instantly reverted.")
