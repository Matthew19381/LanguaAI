"""Events waiting to be delivered to System-Glowny (contract 1.2, INT-2).

A lesson finished while the hub is down must still tick the hub's day plan
once the hub is back, so events are written here in the same transaction as
the action and sent afterwards; the hub deduplicates on
module + user_id + event_type + timestamp, so a resend is harmless.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from backend.database import Base


class HubOutbox(Base):
    __tablename__ = "hub_outbox"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(Text, nullable=False)          # the event as JSON, ready to POST
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(String, nullable=True)
    # Set when the hub accepted it (or rejected it for good: 4xx); NULL = still to send
    done_at = Column(DateTime, nullable=True, index=True)
