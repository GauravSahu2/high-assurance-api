"""
Tests for the SSRF-safe egress client.
Proves that metadata endpoints and private ranges are unreachable.
"""

from unittest.mock import MagicMock, patch

import pytest

from egress_client import SSRFError, safe_get


def test_blocks_aws_metadata_endpoint():
    """169.254.169.254 must be blocked regardless of DNS."""
    with pytest.raises(SSRFError, match="blocklist"):
        safe_get("https://169.254.169.254/latest/meta-data/")


def test_blocks_http_scheme():
    """Only HTTPS is permitted — plain HTTP is rejected."""
    with pytest.raises(SSRFError, match="Scheme"):
        safe_get("http://example.com/data")


def test_blocks_private_range_10():
    """10.x.x.x is a private range and must be blocked."""
    with patch("egress_client.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(None, None, None, None, ("10.0.0.1", 0))]
        with pytest.raises(SSRFError, match="blocked network"):
            safe_get("https://internal-service.example.com/api")


def test_blocks_private_range_172():
    """172.16.x.x is a private range and must be blocked."""
    with patch("egress_client.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(None, None, None, None, ("172.16.0.1", 0))]
        with pytest.raises(SSRFError, match="blocked network"):
            safe_get("https://internal.example.com/api")


def test_blocks_localhost():
    """127.x.x.x loopback must be blocked."""
    with patch("egress_client.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
        with pytest.raises(SSRFError, match="blocked network"):
            safe_get("https://localhost/api")


def test_blocks_gcp_metadata_hostname():
    """GCP metadata hostname must be on the explicit blocklist."""
    with pytest.raises(SSRFError, match="blocklist"):
        safe_get("https://metadata.google.internal/")


def test_allows_public_ip():
    """A legitimate public IP must be allowed through."""
    with patch("egress_client.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 0))]
        with patch("egress_client.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            response = safe_get("https://example.com/data")
            assert response.status_code == 200


def test_rejects_missing_hostname():
    """A URL with no hostname is rejected."""
    with pytest.raises(SSRFError, match="hostname"):
        safe_get("https:///no-host")


def test_ssrf_error_is_value_error_subclass():
    """SSRFError must be a ValueError so callers can catch it generically."""
    assert issubclass(SSRFError, ValueError)

def test_dns_resolution_failure():
    """Simulate a DNS lookup failure (socket.gaierror)."""
    import socket
    with patch("egress_client.socket.getaddrinfo", side_effect=socket.gaierror):
        with pytest.raises(SSRFError, match="resol"):
            safe_get("https://unresolvable-host.internal/api")
