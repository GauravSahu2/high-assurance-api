import json
import os
import time

import pika

from database import SessionLocal
from logger import logger
from models import OutboxEvent


def process_outbox():
    db = SessionLocal()
    try:
        # ── RabbitMQ Setup ──
        RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://admin:admin@rabbitmq:5672/")
        params = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue='hsa_outbox', durable=True)

        # SECURITY: skip_locked=True ensures multiple workers don't grab the same events
        events = db.query(OutboxEvent).with_for_update(skip_locked=True).limit(50).all()

        if not events:
            connection.close()
            return

        for event in events:
            # 1. Publish to RabbitMQ with persistence
            channel.basic_publish(
                exchange='',
                routing_key='hsa_outbox',
                body=json.dumps(event.payload),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    headers={'event_type': event.event_type, 'event_id': event.id}
                )
            )
            logger.info("event_dispatched_rabbitmq", event_id=event.id, type=event.event_type)

            # 2. Delete the event ONLY after successful dispatch
            db.delete(event)

        db.commit()
        connection.close()
        logger.info("outbox_batch_cleared", count=len(events))

    except Exception as e:
        db.rollback()
        logger.error("outbox_worker_error", error=str(e))
        # Ensure connection closes even on logic errors
        try: connection.close()
        except Exception:
            pass
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
