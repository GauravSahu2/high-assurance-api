"""
SSRF-safe HTTP client.
All outbound HTTP requests from the application MUST go through safe_get().
It blocks requests to private/link-local IP ranges and cloud metadata endpoints.
"""

import ipaddress
import socket
from urllib.parse import urlparse

import requests

# Ranges that must never be reachable from this service
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # AWS/GCP/Azure metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

# Explicit hostname blocklist on top of the network check
_BLOCKED_HOSTS = {
    "169.254.169.254",  # AWS IMDS v1
    "metadata.google.internal",
    "metadata.azure.com",
}

ALLOWED_SCHEMES = {"https"}


class SSRFError(ValueError):
    """Raised when a request is blocked by SSRF protection."""


def _resolve_and_check(hostname: str) -> None:
    """Resolve hostname to IP and verify it is not in a blocked range."""
    if hostname in _BLOCKED_HOSTS:
        raise SSRFError(f"Host '{hostname}' is on the explicit blocklist.")
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFError(f"DNS resolution failed for '{hostname}': {e}") from e

    for _, _, _, _, sockaddr in addr_info:
        ip = ipaddress.ip_address(sockaddr[0])
        for network in _BLOCKED_NETWORKS:
            if ip in network:
                raise SSRFError(f"Resolved IP {ip} for host '{hostname}' is in blocked network {network}.")


def safe_get(url: str, timeout: float = 5.0, **kwargs) -> requests.Response:
    """
    Perform a GET request with SSRF protection.
    Raises SSRFError if the target is a private/metadata endpoint.
    Raises requests.exceptions.* on network failures.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SSRFError(f"Scheme '{parsed.scheme}' is not allowed. Only HTTPS is permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("URL has no hostname.")

    _resolve_and_check(hostname)

    return requests.get(url, timeout=timeout, **kwargs)
