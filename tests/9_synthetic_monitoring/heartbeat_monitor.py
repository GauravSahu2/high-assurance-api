import urllib.request
import sys

print("💓 [Tier 9] Sending Synthetic Heartbeat to Target API...")
try:
    response = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)
    if response.getcode() == 200:
        print("✅ [Tier 9] Heartbeat acknowledged. API is healthy and routing traffic.")
        sys.exit(0)
    else:
        print(f"🚨 [FATAL] Unexpected status code: {response.getcode()}")
        sys.exit(1)
except Exception as e:
    print(f"🚨 [FATAL] Synthetic monitor failed to reach API: {e}")
    sys.exit(1)
