"""
Tests for CSV injection sanitisation and Pandera schema validation.
"""

import io
import pytest
from csv_validator import validate_and_sanitize_csv


def _make_csv(rows: list[str], header: str = "user_id,amount,description") -> bytes:
    return ("\n".join([header] + rows) + "\n").encode("utf-8")


# ── Injection sanitisation ────────────────────────────────────────────────────

def test_strips_equals_injection():
    """=cmd|' /C calc' must be stripped to cmd|' /C calc'."""
    csv = _make_csv(["=cmd|' /C calc',100.0,test"])
    df = validate_and_sanitize_csv(csv)
    assert not df["user_id"].iloc[0].startswith("=")


def test_strips_plus_injection():
    """+2+2 formula prefix must be stripped."""
    csv = _make_csv(["+2+2,50.0,test"])
    df = validate_and_sanitize_csv(csv)
    assert not df["user_id"].iloc[0].startswith("+")


def test_strips_minus_injection():
    """-2+3 formula prefix must be stripped."""
    csv = _make_csv(["-2+3,50.0,test"])
    df = validate_and_sanitize_csv(csv)
    assert not df["user_id"].iloc[0].startswith("-")


def test_strips_at_injection():
    """@SUM injection prefix must be stripped."""
    csv = _make_csv(["@SUM(1+1),75.0,test"])
    df = validate_and_sanitize_csv(csv)
    assert not df["user_id"].iloc[0].startswith("@")


def test_strips_multiple_prefix_layers():
    """==cmd (double prefix) must be fully stripped."""
    csv = _make_csv(["==cmd,10.0,test"])
    df = validate_and_sanitize_csv(csv)
    cell = df["user_id"].iloc[0]
    assert not cell.startswith("=")


def test_clean_row_passes_unchanged():
    """A clean row must not be modified."""
    csv = _make_csv(["user_1,100.0,salary"])
    df = validate_and_sanitize_csv(csv)
    assert df["user_id"].iloc[0] == "user_1"
    assert df["amount"].iloc[0] == 100.0


# ── Pandera schema validation ─────────────────────────────────────────────────

def test_rejects_negative_amount():
    """Negative amount must fail schema validation."""
    csv = _make_csv(["user_1,-50.0,test"])
    with pytest.raises(ValueError, match="amount must be non-negative"):
        validate_and_sanitize_csv(csv)


def test_rejects_empty_user_id():
    """Empty user_id must fail schema validation."""
    csv = _make_csv([",100.0,test"])
    with pytest.raises(ValueError):
        validate_and_sanitize_csv(csv)


def test_rejects_empty_file():
    """Empty CSV (header only or no bytes) must be rejected."""
    with pytest.raises(ValueError, match="empty"):
        validate_and_sanitize_csv(b"user_id,amount\n")


def test_rejects_oversized_file():
    """Files exceeding 5 MB must be rejected immediately."""
    big = b"user_id,amount\n" + b"user_1,1.0\n" * 600_000
    with pytest.raises(ValueError, match="too large"):
        validate_and_sanitize_csv(big)


def test_rejects_too_many_rows():
    """CSVs with more than 10,000 rows must be rejected."""
    rows = ["user_1,1.0,test"] * 10_001
    csv = _make_csv(rows)
    with pytest.raises(ValueError, match="rows"):
        validate_and_sanitize_csv(csv)


def test_rejects_malformed_csv():
    """A binary blob that isn't valid CSV must be rejected."""
    with pytest.raises(ValueError, match="empty|parse"):
        validate_and_sanitize_csv(b"\x00\x01\x02\x03")


# ── Upload endpoint integration ───────────────────────────────────────────────

def test_upload_endpoint_accepts_valid_csv(client, auth_header):
    """The /upload-dataset endpoint must accept a clean CSV and return row count."""
    csv_bytes = _make_csv(["user_1,100.0,salary", "user_2,200.0,bonus"])
    data = {"file": (io.BytesIO(csv_bytes), "data.csv")}
    res = client.post(
        "/upload-dataset",
        data=data,
        headers=auth_header,
        content_type="multipart/form-data",
    )
    assert res.status_code == 202
    assert res.get_json().get("status") == "processing"


def test_upload_endpoint_rejects_injection_survives_validation(client, auth_header):
    """An injection-laden CSV where injections are stripped and schema passes must succeed."""
    csv_bytes = _make_csv(["=user_1,100.0,safe"])
    data = {"file": (io.BytesIO(csv_bytes), "data.csv")}
    res = client.post(
        "/upload-dataset",
        data=data,
        headers=auth_header,
        content_type="multipart/form-data",
    )
    assert res.status_code == 202


def test_upload_endpoint_rejects_non_csv(client, auth_header):
    """Non-CSV file extension must be rejected with 400."""
    data = {"file": (io.BytesIO(b"some binary data"), "data.pkl")}
    res = client.post(
        "/upload-dataset",
        data=data,
        headers=auth_header,
        content_type="multipart/form-data",
    )
    assert res.status_code == 400


def test_upload_endpoint_requires_auth(client):
    """Unauthenticated upload must return 401."""
    csv_bytes = _make_csv(["user_1,100.0,test"])
    data = {"file": (io.BytesIO(csv_bytes), "data.csv")}
    res = client.post(
        "/upload-dataset",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 401


def test_upload_endpoint_rejects_schema_violation(client, auth_header):
    """CSV with negative amount must return 422."""
    csv_bytes = _make_csv(["user_1,-50.0,bad"])
    data = {"file": (io.BytesIO(csv_bytes), "data.csv")}
    res = client.post(
        "/upload-dataset",
        data=data,
        headers=auth_header,
        content_type="multipart/form-data",
    )
    assert res.status_code == 422


def test_upload_endpoint_rejects_missing_file(client, auth_header):
    """Request with no file field must return 400."""
    res = client.post(
        "/upload-dataset",
        data={},
        headers=auth_header,
        content_type="multipart/form-data",
    )
    assert res.status_code == 400

def test_csv_parser_exception():
    """Simulate a catastrophic failure in the underlying CSV parsing engine."""
    from unittest.mock import patch
    with patch("csv_validator.pd.read_csv", side_effect=Exception("Simulated crash")):
        with pytest.raises(ValueError, match="Failed to parse CSV"):
            validate_and_sanitize_csv(b"user_id,amount\n1,10.0")
