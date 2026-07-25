"""Send browser Web Push notifications (VAPID / RFC 8291).

Mirrors the project's "graceful when unconfigured" convention: with no VAPID keys
set, ``push_enabled()`` is False and sends are skipped — exactly like an empty
DISCORD_WEBHOOK_URL. A subscription the push service reports as gone (404/410) is
pruned so a dead device is not retried forever.

pywebpush is imported lazily so the app still boots if the dependency has not
been installed yet in a given environment.
"""
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


def push_enabled() -> bool:
    """True only when both VAPID keys are configured."""
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def build_payload(title: str, body: str, url: str = "/", tag: Optional[str] = None) -> str:
    """Serialize a notification for the service worker's push handler."""
    return json.dumps({"title": title, "body": body, "url": url, "tag": tag})


def upsert_subscription(db: Session, user_id: int, subscription: dict) -> PushSubscription:
    """Store (or refresh) a browser subscription, keyed on its endpoint.

    Re-subscribing the same browser yields the same endpoint, so we update the
    keys and owner in place instead of creating duplicates.
    """
    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys") or {}
    p256dh, auth = keys.get("p256dh"), keys.get("auth")
    if not endpoint or not p256dh or not auth:
        raise ValueError("subscription must include endpoint and keys.p256dh/auth")

    row = db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint
    ).first()
    if row:
        row.user_id = user_id
        row.p256dh = p256dh
        row.auth = auth
    else:
        row = PushSubscription(user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def remove_subscription(db: Session, endpoint: str) -> int:
    """Delete a subscription by endpoint. Returns how many rows were removed."""
    deleted = db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint
    ).delete(synchronize_session=False)
    db.commit()
    return deleted


def _send_one(subscription: PushSubscription, payload: str) -> bool:
    """Send to a single subscription. Returns True on success.

    Raises the pywebpush exception on a gone subscription so the caller can prune.
    """
    from pywebpush import webpush

    webpush(
        subscription_info={
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        },
        data=payload,
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": settings.VAPID_SUBJECT},
    )
    return True


def send_to_user(db: Session, user_id: int, payload: str) -> dict:
    """Send a payload to every subscription of a user.

    Prunes subscriptions the push service reports as gone (404/410). Returns
    ``{"sent": n, "pruned": m, "enabled": bool}``.
    """
    if not push_enabled():
        return {"sent": 0, "pruned": 0, "enabled": False}

    subs = db.query(PushSubscription).filter(
        PushSubscription.user_id == user_id
    ).all()

    sent = 0
    pruned = 0
    for sub in subs:
        try:
            _send_one(sub, payload)
            sent += 1
        except Exception as e:  # noqa: BLE001 — pywebpush raises WebPushException
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):
                # Subscription is permanently gone — drop it.
                db.delete(sub)
                pruned += 1
            else:
                logger.warning("Web push to sub %s failed: %s", sub.id, e)
    if pruned:
        db.commit()
    return {"sent": sent, "pruned": pruned, "enabled": True}
