import pytest
from jsonschema import validate, ValidationError

# 1. The Frontend (Consumer) defines the STRICT Contract (JSON Schema)
# It says: "The backend MUST return a 'user_id' as an integer, and 'status' as a string."
FRONTEND_CONTRACT = {
    "type": "object",
    "properties": {
        "user_id": {"type": "integer"},
        "status": {"type": "string"}
    },
    "required": ["user_id", "status"],
    "additionalProperties": False  # STRICT RULE: No extra undocumented fields allowed!
}

def test_frontend_backend_contract():
    # 2. Simulate a GOOD Backend response
    good_backend_response = {
        "user_id": 123,
        "status": "active"
    }
    
    # 3. Simulate a BUGGY Backend response (Developer accidentally changed 'user_id' to 'id')
    bad_backend_response = {
        "id": 123, 
        "status": "active"
    }

    # 4. THE ASSERTION: The good response MUST pass the contract
    try:
        validate(instance=good_backend_response, schema=FRONTEND_CONTRACT)
        print("\n[SUCCESS] Good response mathematically matches the Frontend Contract.")
    except ValidationError as e:
        pytest.fail(f"CRITICAL: Contract broken on good response: {e.message}")

    # 5. THE ASSERTION: The bad response MUST throw an error and fail the build
    try:
        validate(instance=bad_backend_response, schema=FRONTEND_CONTRACT)
        pytest.fail("CRITICAL: The contract test FAILED to catch the backend bug!")
    except ValidationError as e:
        print(f"[SUCCESS] Contract Enforcement caught the Backend bug! Error prevented: '{e.message}'")

