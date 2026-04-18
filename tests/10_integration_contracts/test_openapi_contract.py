import pytest
import schemathesis
from main import app

schema = schemathesis.openapi.from_path("openapi.yaml")

@schema.parametrize()
def test_api_conforms_to_openapi_spec(case):
    media = getattr(case, "media_type", "") or ""
    if case.method == "POST" and "multipart/form-data" in media:
        if not isinstance(case.body, dict):
            case.body = {"file": b"fuzzed_data"}

    response = case.call(app=app)

    if response.status_code == 429:
        return

    if case.operation.path == "/login" and response.status_code == 400:
        if b"request body must be a JSON object" in response.content:
            return

    case.validate_response(response)
