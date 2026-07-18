"""Idempotency ledger for actions performed offline and replayed on reconnect.

A client that practises without a network queues each action locally and replays
it once back online. Replays can happen more than once (retry, reinstall, two
tabs), so every queued action carries a client-generated ``client_event_id``.
The unique constraint here is what stops a single answer from being counted
twice in FSRS scheduling and exposure counters.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from backend.database import Base


class SyncEvent(Base):
    __tablename__ = "sync_events"

    id = Column(Integer, primary_key=True, index=True)
    # UUID generated on the device when the action happened
    client_event_id = Column(String, nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String, nullable=False)          # e.g. "exercise_answer"
    target_id = Column(Integer, nullable=True)     # e.g. the exercise id
    # When the learner actually performed it (not when it reached the server)
    occurred_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
