import pytest
from routes.route_utils import _revoke_jti
from telemetry import _get_or_create_counter, _get_or_create_histogram

def test_revoke_jti_missing_claims():
    # Covers line 42 in route_utils.py
    assert _revoke_jti(None, {}) is None
    assert _revoke_jti(None, {"jti": "some"}) is None
    assert _revoke_jti(None, {"exp": 123}) is None

def test_get_or_create_metrics_already_exists():
    # Covers lines 59 and 67 in telemetry.py
    c1 = _get_or_create_counter("test_counter", "desc", ["l1"])
    c2 = _get_or_create_counter("test_counter", "desc", ["l1"])
    assert c1 is c2

    h1 = _get_or_create_histogram("test_histogram", "desc", ["l1"])
    h2 = _get_or_create_histogram("test_histogram", "desc", ["l1"])
    assert h1 is h2
