"""Kafka consumer: turns ANALYSIS_COMPLETED events into user notifications.

This demonstrates the event-driven decoupling: the AI worker doesn't know or
care that notifications exist — it just publishes a fact. This consumer (and any
future analytics/audit/email consumer) reacts independently. You could add more
consumers in their own group without touching the producer."""

import json
import time

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.init_db import init_db
from app.db.models import AuditLog, Notification
from app.db.session import SessionLocal
from app.services.events import Event

setup_logging()
log = get_logger("consumer")


def _handle(envelope: dict) -> None:
    event_type = envelope.get("event_type")
    payload = envelope.get("payload", {})

    db = SessionLocal()
    try:
        # Every event becomes an audit record (a second, independent reaction).
        db.add(AuditLog(
            user_id=payload.get("user_id"),
            action=event_type or "UNKNOWN",
            entity="job",
            entity_id=payload.get("job_id", ""),
        ))

        if event_type == Event.ANALYSIS_COMPLETED:
            user_id = payload.get("user_id")
            if user_id:
                db.add(Notification(
                    user_id=user_id,
                    title="Analysis complete",
                    body=f"Your {payload.get('type', 'job')} analysis is ready: "
                         f"{payload.get('summary', '')[:200]}",
                ))
                # In production this is where you'd send an email/push.
                log.info("[email] notified user %s about job %s",
                         user_id, payload.get("job_id"))
        db.commit()
    finally:
        db.close()


def main() -> None:
    init_db()  # ensure tables exist if the consumer starts first
    from kafka import KafkaConsumer

    # Retry connecting until Kafka is ready.
    consumer = None
    for attempt in range(30):
        try:
            consumer = KafkaConsumer(
                settings.kafka_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                group_id="notification-service",
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda v: json.loads(v.decode()),
            )
            break
        except Exception as exc:
            log.warning("Kafka not ready (attempt %d): %s", attempt + 1, exc)
            time.sleep(3)

    if consumer is None:
        log.error("Could not connect to Kafka, exiting")
        return

    log.info("notification consumer listening on '%s'", settings.kafka_topic)
    for message in consumer:
        try:
            _handle(message.value)
        except Exception:
            log.exception("failed to handle event")


if __name__ == "__main__":
    main()
