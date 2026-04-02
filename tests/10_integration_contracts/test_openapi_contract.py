import os

import pytest
import schemathesis
from main import app  # noqa: E402

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

for _candidate in [
    os.path.join(BASE_DIR, "src", "openapi.yaml"),
    os.path.join(BASE_DIR, "openapi.yaml"),
]:
    if os.path.exists(_candidate):
        SCHEMA_PATH = _candidate
        break
else:
    pytest.skip("openapi.yaml not found", allow_module_level=True)

if os.getenv("MUTMUT_TESTING") == "true":
    pytest.skip("schemathesis skipped during mutation testing", allow_module_level=True)

with open(SCHEMA_PATH, "rb") as f:
    _schema_bytes = f.read()

if "/_schema" not in [rule.rule for rule in app.url_map.iter_rules()]:

    @app.route("/_schema")
    def _serve_schema():
        from flask import Response

        return Response(_schema_bytes, mimetype="application/yaml")


schema = schemathesis.openapi.from_wsgi("/_schema", app)


@schema.parametrize()
def test_api_conforms_to_openapi_spec(case):
    with app.test_client() as c:
        c.post("/test/reset")

    # FIXED: Explicitly use call_wsgi() for local routing in Schemathesis 3.25+
    response = case.call_wsgi(app=app)
    case.validate_response(response)
