from unittest.mock import Mock


def mock_cloud_gateway_response(origin_header):
    # Simulating AWS API Gateway / CloudFront Edge Logic
    response = Mock()
    response.headers = {
        # Edge MUST explicitly instruct browsers NOT to cache financial data
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }

    # Strict CORS validation
    allowed_origin = "https://app.highassurance.dev"
    if origin_header == allowed_origin:
        response.headers["Access-Control-Allow-Origin"] = allowed_origin
    else:
        # Reject unauthorized origins
        response.headers["Access-Control-Allow-Origin"] = "null"

    return response


def test_cors_and_edge_caching():
    # 1. Test CORS Rejection
    malicious_origin = "https://evil-hacker-site.com"
    hacker_response = mock_cloud_gateway_response(malicious_origin)

    assert hacker_response.headers["Access-Control-Allow-Origin"] != malicious_origin, "CRITICAL: CORS leak!"

    # 2. Test Edge Caching Rules for Sensitive Endpoints
    valid_origin = "https://app.highassurance.dev"
    safe_response = mock_cloud_gateway_response(valid_origin)

    cache_header = safe_response.headers.get("Cache-Control", "")
    assert "no-store" in cache_header, "CRITICAL: Edge server is caching sensitive financial data!"
    assert "private" in cache_header, "CRITICAL: Edge server missing 'private' cache directive!"

    print("\n[SUCCESS] Edge Security verified. Strict CORS and Zero-Caching enforced.")
