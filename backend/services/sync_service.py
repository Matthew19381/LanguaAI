"""Shared plumbing for replaying actions performed offline.

Both exercise answers and flashcard reviews are queued on the device and
replayed on reconnect. They need the same two guarantees:

1. **Exactly once** — a retried replay must not apply the review twice, which
   would corrupt FSRS scheduling and exposure counters.
2. **Correct timing** — the review is scheduled from when the learner actually
   did it, not from when the device happened to reconnect.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.sync_event import SyncEvent


def parse_occurred_at(raw: Optional[str]) -> datetime:
    """Parse a client timestamp, falling back to now. Never trusts the future."""
    now = datetime.now(timezone.utc)
    if not raw:
        return now
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return now
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    # A device clock running ahead must not push reviews into the future
    return min(parsed, now)


def already_applied(db: Session, client_event_id: Optional[str]) -> bool:
    """True if this queued action has already been replayed successfully."""
    if not client_event_id:
        return False
    return db.query(SyncEvent).filter(
        SyncEvent.client_event_id == client_event_id
    ).first() is not None


def record_event(
    db: Session,
    client_event_id: Optional[str],
    user_id: int,
    kind: str,
    target_id: Optional[int] = None,
    occurred_at: Optional[datetime] = None,
) -> None:
    """Stage the idempotency marker. Caller commits (with the review itself)."""
    if not client_event_id:
        return
    db.add(SyncEvent(
        client_event_id=client_event_id,
        user_id=user_id,
        kind=kind,
        target_id=target_id,
        occurred_at=occurred_at,
    ))
