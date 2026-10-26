"""Publisher of LinguaAI events to System-Glowny (INT-2, contract 1.2).

The hub ticks its day-plan item "LinguaAI: lekcja dnia" when it receives
``lesson_completed`` (the item's ``complete_on``, see routers/integration.py).
Delivery goes through the ``hub_outbox`` table: a network error never blocks
the learner, and pending events are retried on the next event and at startup.

Configuration (same names the hub's provision_module_keys.py writes):
SYSTEM_GLOWNY_URL and SYSTEM_GLOWNY_MODULE_KEY, read from the environment,
the root .env, or backend/.env (where the provisioning script puts them).
No key = publishing disabled. Under pytest (TESTING=1) it is always disabled
unless a test patches ``hub_config``.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from dotenv import dotenv_values
from sqlalchemy.orm import Session

from backend.config import REPO_ROOT
from backend.models.hub_outbox import HubOutbox

logger = logging.getLogger(__name__)

MODULE_NAME = "lingua-ai"
DEFAULT_URL = "http://127.0.0.1:8000"
EVENT_PATH = "/api/v1/integrations/event"
TIMEOUT_SECONDS = 3.0
MAX_ATTEMPTS = 50  # ~ one attempt per lesson/startup; then left for inspection
FLUSH_BATCH = 20


def _from_files(name: str) -> str:
    for path in (REPO_ROOT / ".env", REPO_ROOT / "backend" / ".env"):
        if path.is_file():
            value = dotenv_values(path).get(name)
            if value:
                return value.strip()
    return ""


def hub_config() -> tuple[str, str]:
    """(hub base URL, module key); an empty key disables publishing."""
    if os.environ.get("TESTING") == "1":
        return "", ""
    key = os.environ.get("SYSTEM_GLOWNY_MODULE_KEY") or _from_files("SYSTEM_GLOWNY_MODULE_KEY")
    url = os.environ.get("SYSTEM_GLOWNY_URL") or _from_files("SYSTEM_GLOWNY_URL") or DEFAULT_URL
    return url.rstrip("/"), key


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def lesson_completed_event(lesson) -> dict:
    """Contract 1.2 event for a completed lesson; timestamp = when it was finished
    (an offline completion synced later still ticks the day it happened)."""
    try:
        content = json.loads(lesson.content) if isinstance(lesson.content, str) else (lesson.content or {})
    except (TypeError, ValueError):
        content = {}
    if not isinstance(content, dict):
        content = {}
    data = {
        "lesson_id": lesson.id,
        "day_number": lesson.day_number,
        "topic": lesson.topic,
        "language": lesson.language,
        "cefr_level": lesson.cefr_level,
    }
    for field in ("module_id", "day_type"):
        if content.get(field):
            data[field] = content[field]
    return {
        "event_type": "lesson_completed",
        "module": MODULE_NAME,
        "user_id": str(lesson.user_id),
        "timestamp": _iso_utc(lesson.completed_at or datetime.now(timezone.utc)),
        "data": data,
        "tags": ["learning"],
    }


def enqueue(db: Session, event: dict) -> Optional[HubOutbox]:
    """Add an event to the outbox (caller commits). Nothing is stored when
    publishing is disabled, so a setup without the hub keeps no backlog."""
    _url, key = hub_config()
    if not key:
        return None
    row = HubOutbox(event_type=event["event_type"], payload=json.dumps(event, ensure_ascii=False))
    db.add(row)
    return row


def flush(db: Session, transport: Optional[httpx.BaseTransport] = None) -> dict:
    """Send pending events; returns counts. Never raises."""
    url, key = hub_config()
    sent = rejected = failed = 0
    if not key:
        return {"sent": 0, "rejected": 0, "failed": 0}
    try:
        rows = (
            db.query(HubOutbox)
            .filter(HubOutbox.done_at.is_(None), HubOutbox.attempts < MAX_ATTEMPTS)
            .order_by(HubOutbox.id)
            .limit(FLUSH_BATCH)
            .all()
        )
        if not rows:
            return {"sent": 0, "rejected": 0, "failed": 0}
        with httpx.Client(timeout=TIMEOUT_SECONDS, transport=transport) as client:
            for row in rows:
                row.attempts = (row.attempts or 0) + 1
                try:
                    resp = client.post(url + EVENT_PATH, content=row.payload,
                                       headers={"Content-Type": "application/json", "X-Module-Key": key})
                except httpx.HTTPError as exc:
                    row.last_error = f"network: {type(exc).__name__}"[:250]
                    failed += 1
                    break  # hub unreachable: keep the rest for the next flush
                if resp.status_code < 300:
                    row.done_at = datetime.now(timezone.utc)
                    row.last_error = None
                    sent += 1
                elif 400 <= resp.status_code < 500:
                    # Wrong key (403) or payload (422): a resend cannot succeed
                    row.done_at = datetime.now(timezone.utc)
                    row.last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    rejected += 1
                    logger.warning("Hub rejected %s event: %s", row.event_type, row.last_error)
                else:
                    row.last_error = f"HTTP {resp.status_code}"
                    failed += 1
                    break
        db.commit()
    except Exception:
        logger.exception("Hub outbox flush failed")
        db.rollback()
    return {"sent": sent, "rejected": rejected, "failed": failed}


# Tests point these at the test database and a fake hub
session_factory = None
transport: Optional[httpx.BaseTransport] = None


def flush_in_new_session() -> None:
    """For BackgroundTasks / startup: own DB session, never raises."""
    if not hub_config()[1]:
        return
    if session_factory is None:
        from backend.database import SessionLocal as factory
    else:
        factory = session_factory
    db = factory()
    try:
        flush(db, transport=transport)
    finally:
        db.close()
