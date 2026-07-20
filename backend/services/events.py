"""Kafka event publishing.

Kafka is the EVENT backbone: producers announce facts ("this happened") and any
number of independent consumers react. This is different from Celery, which runs
the actual work ("do this"). The API and the workers publish events here; the
notification consumer (and future analytics/audit consumers) read them.

The producer is fail-soft: if Kafka is down, we log and continue so the core
flow never breaks because of the event bus."""

import json
import time

from config.settings import settings
from utils.logger import get_logger

log = get_logger("events")


# Event type constants (the vocabulary of the platform).
class Event:
    WEBSITE_SUBMITTED = "WEBSITE_SUBMITTED"
    FILE_UPLOADED = "FILE_UPLOADED"
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    REPORT_GENERATED = "REPORT_GENERATED"


_producer = None


def _get_producer():
    """Lazily build a KafkaProducer. Returns None if Kafka is unavailable."""
    global _producer
    if not settings.kafka_enabled:
        return None
    if _producer is not None:
        return _producer
    try:
        from kafka import KafkaProducer

        _producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode(),
            key_serializer=lambda k: k.encode() if k else None,
            retries=3,
            linger_ms=20,
        )
    except Exception as exc:  # broker not ready yet, etc.
        log.warning("Kafka producer unavailable: %s", exc)
        _producer = None
    return _producer


def publish(event_type: str, payload: dict, key: str | None = None) -> None:
    """Publish an event to the platform topic. Key = job_id keeps all events for
    one job on the same partition (so they stay ordered)."""
    producer = _get_producer()
    envelope = {
        "event_type": event_type,
        "occurred_at": time.time(),
        "payload": payload,
    }
    if producer is None:
        log.info("[event:skipped-no-kafka] %s %s", event_type, payload)
        return
    try:
        producer.send(settings.kafka_topic, key=key, value=envelope)
        producer.flush(timeout=5)
        log.info("[event] %s key=%s", event_type, key)
    except Exception as exc:
        log.warning("Failed to publish %s: %s", event_type, exc)
