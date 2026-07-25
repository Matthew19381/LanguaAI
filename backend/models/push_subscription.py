"""Browser Web Push subscriptions.

Each row is one device/browser that opted in to notifications for a user. The
push ``endpoint`` (a URL at the browser vendor's push service) is the natural
unique key: re-subscribing the same browser returns the same endpoint, so we
upsert on it rather than pile up duplicates. ``p256dh`` and ``auth`` are the
client's public key and auth secret, needed to encrypt the payload (RFC 8291).
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from backend.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # The push service URL the browser gave us; unique so re-subscribing upserts.
    endpoint = Column(Text, nullable=False, unique=True, index=True)
    p256dh = Column(String, nullable=False)  # client public key (base64url)
    auth = Column(String, nullable=False)    # client auth secret (base64url)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
