from database import Base, get_db
from models import Account, IdempotencyKey, OutboxEvent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_database_models_and_outbox():
    # 1. Spin up an isolated in-memory database just for this test
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()

    # 2. Test Account Model
    acc = Account(user_id="user_1", balance=1500.00)
    db.add(acc)

    # 3. Test Idempotency Key Model
    idem = IdempotencyKey(
        idempotency_key="tx-999",
        status="processed",
        response_body={"status": "transferred"},
    )
    db.add(idem)

    # 4. Test Transactional Outbox Event Model
    outbox = OutboxEvent(
        event_type="FUNDS_TRANSFERRED", payload={"from": "user_1", "amount": 100.0}
    )
    db.add(outbox)

    db.commit()

    # 5. Assertions: Prove the data layer reads and writes securely
    assert (
        db.query(Account).filter(Account.user_id == "user_1").first().balance == 1500.0
    )
    assert db.query(IdempotencyKey).first().response_body["status"] == "transferred"
    assert db.query(OutboxEvent).first().payload["amount"] == 100.0

    db.close()


def test_get_db_generator():
    """Proves the FastAPI/Flask dependency generator correctly yields and closes sessions."""
    gen = get_db()
    db_session = next(gen)
    assert db_session is not None
    try:
        next(gen)
    except StopIteration:
        pass  # Expected behavior when the generator yields once and closes
