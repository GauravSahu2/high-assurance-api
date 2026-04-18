import os
import time

from database import SessionLocal
from logger import logger
from models import OutboxEvent


def process_outbox():
    db = SessionLocal()
    try:
        # SECURITY: skip_locked=True ensures multiple workers don't grab the same events
        events = db.query(OutboxEvent).with_for_update(skip_locked=True).limit(50).all()

        if not events:
            return

        for event in events:
            # 1. Simulate sending to AWS SQS, Kafka, or triggering an email
            logger.info("event_dispatched", event_id=event.id, type=event.event_type, payload=event.payload)

            # 2. Delete the event ONLY after successful dispatch
            db.delete(event)

        db.commit()
        logger.info("outbox_batch_cleared", count=len(events))

    except Exception as e:
        db.rollback()
        logger.error("outbox_worker_error", error=str(e))
    finally:
        db.close()

if __name__ == "__main__":  # pragma: no cover
    logger.info("outbox_worker_started", mode="polling")

    # In tests, we only want to run it once and exit. In prod, we loop forever.
    if os.environ.get("TEST_MODE"):
        process_outbox()
    else:
        while True:
            process_outbox()
            time.sleep(2)  # Poll every 2 seconds
