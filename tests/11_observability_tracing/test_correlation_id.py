import pytest
from unittest.mock import patch
import uuid

# Mocking the API's internal function that calls a downstream service
def internal_api_logic(headers):
    correlation_id = headers.get("X-Correlation-ID")
    if not correlation_id:
        return 400, "Missing Trace ID"
    
    # The API MUST pass this exact ID to the downstream database/service
    downstream_headers = {"X-Correlation-ID": correlation_id}
    return 200, downstream_headers

def test_traceability_chain():
    # 1. Generate a unique trace ID at the Edge
    trace_id = str(uuid.uuid4())
    incoming_headers = {"X-Correlation-ID": trace_id}
    
    # 2. Execute the API logic
    status, downstream_headers = internal_api_logic(incoming_headers)
    
    # 3. THE ASSERTION: The downstream service MUST receive the exact same trace ID
    assert status == 200
    assert downstream_headers.get("X-Correlation-ID") == trace_id, "CRITICAL: The trace chain was broken!"
    print(f"\n[SUCCESS] Distributed Tracing verified. Correlation ID {trace_id} successfully propagated.")
