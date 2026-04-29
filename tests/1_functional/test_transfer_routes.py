import pytest
from main import app as flask_app
from auth import generate_jwt
from database import SessionLocal
from models import Account

@pytest.fixture
def user1_token():
    return generate_jwt("user_1", "user")

@pytest.fixture
def setup_balances():
    db = SessionLocal()
    u1 = db.query(Account).filter_by(user_id="user_1").first()
    u2 = db.query(Account).filter_by(user_id="user_2").first()
    if u1:
        u1.balance = 1000.00
    if u2:
        u2.balance = 500.00
    db.commit()
    db.close()

def test_transfer_success(user1_token, setup_balances):
    with flask_app.test_client() as c:
        payload = {
            "to_user": "user_2",
            "amount": 100.50
        }
        headers = {
            "Authorization": f"Bearer {user1_token}",
            "X-Idempotency-Key": "unique-key-123"
        }
        resp = c.post("/transfer", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "transferred"
        
        # Verify idempotency
        resp2 = c.post("/transfer", json=payload, headers=headers)
        assert resp2.status_code == 409 # duplicate transaction

def test_transfer_insufficient_funds(user1_token):
    db = SessionLocal()
    u1 = db.query(Account).filter_by(user_id="user_1").first()
    if u1:
        u1.balance = 10.00
        db.commit()
    db.close()
    
    with flask_app.test_client() as c:
        payload = {
            "to_user": "user_2",
            "amount": 50.00
        }
        headers = {
            "Authorization": f"Bearer {user1_token}",
            "X-Idempotency-Key": "broke-key"
        }
        resp = c.post("/transfer", json=payload, headers=headers)
        assert resp.status_code == 400
        assert "insufficient funds" in resp.get_json()["error"].lower()

def test_transfer_self(user1_token):
    with flask_app.test_client() as c:
        payload = {
            "to_user": "user_1",
            "amount": 10.00
        }
        headers = {
            "Authorization": f"Bearer {user1_token}",
            "X-Idempotency-Key": "self-key"
        }
        resp = c.post("/transfer", json=payload, headers=headers)
        assert resp.status_code == 400
        assert "cannot transfer to self" in resp.get_json()["error"].lower()
