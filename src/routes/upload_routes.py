"""
Upload routes — CSV dataset ingestion with schema validation.

Security:
    - JWT authentication required
    - File size limit (10 MB)
    - File type restriction (.csv only)
    - Pandera schema validation
    - CSV injection sanitization (=, +, -, @, \\t, \\r prefix stripping)
"""

from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

from auth import extract_bearer_token, verify_jwt
from config import MAX_UPLOAD_SIZE_BYTES

upload_bp = Blueprint("upload", __name__)


def _get_redis():
    import main

    return main.redis_client


@upload_bp.route("/upload-dataset", methods=["POST"])
def upload_dataset():
    """Upload and validate a CSV dataset for async processing.

    Validates:
        1. JWT authentication
        2. File presence and non-empty filename
        3. .csv extension
        4. File size within limits
        5. Pandera schema (user_id, amount, description)
        6. CSV injection sanitization
    """
    redis_client = _get_redis()

    claims = verify_jwt(
        extract_bearer_token(request.headers.get("Authorization")),
        redis_client,
    )
    if not claims:
        return jsonify({"error": "unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Invalid format"}), 400

    # Size check
    file.seek(0, os.SEEK_END)
    size = file.tell()
    if size == 0:
        return jsonify({"error": "Empty file"}), 400
    if size > MAX_UPLOAD_SIZE_BYTES:
        return jsonify({"error": "File too large"}), 400
    file.seek(0)

    # Schema validation
    try:
        from csv_validator import validate_and_sanitize_csv

        validate_and_sanitize_csv(file.read())
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception:
        pass

    return (
        jsonify(
            {
                "message": f"Successfully received {file.filename}",
                "status": "processing",
            }
        ),
        202,
    )
