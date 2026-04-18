"""
Coverage tests for upload endpoint edge cases.

These tests exercise the upload validation branches that are not
reached by Schemathesis fuzzing (file size, empty name, too-large).
"""
import io
import os

import pytest


def test_upload_empty_filename(client, auth_header):
    """Covers upload_routes.py line 54 — empty filename rejection."""
    data = {"file": (io.BytesIO(b"data"), "")}
    res = client.post(
        "/upload-dataset",
        headers=auth_header,
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert "filename" in res.get_json()["error"].lower() or "Empty" in res.get_json()["error"]


def test_upload_empty_file(client, auth_header):
    """Covers upload_routes.py line 62 — empty file rejection."""
    data = {"file": (io.BytesIO(b""), "test.csv")}
    res = client.post(
        "/upload-dataset",
        headers=auth_header,
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert "Empty" in res.get_json()["error"] or "empty" in res.get_json()["error"].lower()


def test_upload_file_too_large(client, auth_header):
    """Covers upload_routes.py line 64 — oversized file rejection."""
    from unittest.mock import patch
    # Patch MAX_UPLOAD_SIZE_BYTES to a small value for testing
    with patch("routes.upload_routes.MAX_UPLOAD_SIZE_BYTES", 5):
        data = {"file": (io.BytesIO(b"this is more than 5 bytes"), "test.csv")}
        res = client.post(
            "/upload-dataset",
            headers=auth_header,
            data=data,
            content_type="multipart/form-data",
        )
    assert res.status_code == 400
    assert "large" in res.get_json()["error"].lower()
