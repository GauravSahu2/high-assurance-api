# tests/9_synthetic_monitoring/heartbeat_monitor.py
import requests
import time

def run_synthetic_heartbeat():
    # A list of critical internal and external services your app relies on
    CRITICAL_SERVICES = {
        "Payment Gateway": "https://api.stripe.com/healthcheck",
        "Identity Provider": "https://cdn.auth0.com/client/health"
    }

    for service_name, url in CRITICAL_SERVICES.items():
        try:
            # Set a strict 3-second timeout. Slow APIs are broken APIs.
            response = requests.get(url, timeout=3.0)
            
            # 1. Check if the API is alive (200 OK)
            if response.status_code == 200:
                print(f"[HEALTHY] {service_name} is online and responding.")
            # 2. Check if the API endpoint was moved or deprecated (404 Not Found)
            elif response.status_code == 404:
                print(f"[FATAL ERROR] {service_name} endpoint missing! Did the API version change?")
            else:
                print(f"[WARNING] {service_name} returned abnormal status: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"[ALERT] {service_name} timed out! Degraded performance detected.")
        except requests.exceptions.ConnectionError:
            print(f"[FATAL ERROR] {service_name} is completely unreachable.")

if __name__ == "__main__":
    print("=== Initiating Synthetic Health Check ===")
    run_synthetic_heartbeat()
