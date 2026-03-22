import os

import pytest
import schemathesis
from main import app  # noqa: E402

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Resolve schema path — works in normal layout and mutmut mutants/ layout
for _candidate in [
    os.path.join(BASE_DIR, "src", "openapi.yaml"),
    os.path.join(BASE_DIR, "openapi.yaml"),
]:
    if os.path.exists(_candidate):
        SCHEMA_PATH = _candidate
        break
else:
    pytest.skip("openapi.yaml not found", allow_module_level=True)

import os

if os.getenv("MUTMUT_TESTING") == "true":
    pytest.skip("schemathesis skipped during mutation testing", allow_module_level=True)

with open(SCHEMA_PATH, "rb") as f:
    _schema_bytes = f.read()

# Guard against double-registration when pytest re-imports this module
if "/_schema" not in [rule.rule for rule in app.url_map.iter_rules()]:

    @app.route("/_schema")
    def _serve_schema():
        from flask import Response

        return Response(_schema_bytes, mimetype="application/yaml")


schema = schemathesis.openapi.from_wsgi("/_schema", app)


@schema.parametrize()
def test_api_conforms_to_openapi_spec(case):
    import main as _main

    _main.failed_login_attempts.clear()
    _main.processed_transactions.clear()
    _main.accounts["user_1"] = 1000.0
    _main.accounts["user_2"] = 500.0
    response = case.call()
    case.validate_response(response)
