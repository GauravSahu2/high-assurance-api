from unittest.mock import patch

from database import get_db
from models import OutboxEvent
from worker import process_outbox


def test_worker_processes_and_deletes_events():
    db = next(get_db())
    # Insert a fake event
    event = OutboxEvent(event_type="TEST_EVENT", payload={"msg": "hello"})
    db.add(event)
    db.commit()

    # Process it
    process_outbox()

    # Verify it was safely deleted from the outbox
    remaining = db.query(OutboxEvent).count()
    assert remaining == 0


def test_worker_handles_connection_error():
    """Test that the worker handles connection failures gracefully (Covering except block)."""
    with patch("pika.BlockingConnection") as mock_conn:
        mock_conn.side_effect = Exception("RabbitMQ Unreachable")
        # should not raise exception, just log it
        process_outbox()


def test_worker_handles_exception():
    # Simulate a catastrophic database failure during processing
    with patch("worker.SessionLocal") as mock_session:
        mock_db = mock_session.return_value
        mock_db.query.side_effect = Exception("Simulated DB Failure")

        # The worker must catch the error, log it, rollback, and NOT crash
        process_outbox()
        mock_db.rollback.assert_called_once()


def test_worker_empty_outbox():
    # Ensures the worker safely returns when no events exist
    db = next(get_db())
    db.query(OutboxEvent).delete()
    db.commit()

    process_outbox()  # Should gracefully exit
