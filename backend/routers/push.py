"""Web Push API — expose the VAPID public key, manage subscriptions, test send."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.schemas.push import SubscribeRequest, UnsubscribeRequest
from backend.services import push_service
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/push/vapid-public-key")
async def get_vapid_public_key():
    """The browser needs this as its applicationServerKey to subscribe.

    Returns ``enabled: false`` (not an error) when push is unconfigured, so the
    frontend can simply hide the toggle.
    """
    return {
        "enabled": push_service.push_enabled(),
        "public_key": settings.VAPID_PUBLIC_KEY or None,
    }


@router.post("/api/push/subscribe")
async def subscribe(request: SubscribeRequest, db: Session = Depends(get_db)):
    """Register (or refresh) a browser subscription for a user."""
    get_user_or_404(db, request.user_id)
    try:
        row = push_service.upsert_subscription(
            db, request.user_id, request.subscription.model_dump()
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"success": True, "subscription_id": row.id}


@router.post("/api/push/unsubscribe")
async def unsubscribe(request: UnsubscribeRequest, db: Session = Depends(get_db)):
    """Remove a subscription by its endpoint (e.g. the user turned push off)."""
    removed = push_service.remove_subscription(db, request.endpoint)
    return {"success": True, "removed": removed}


@router.post("/api/push/test/{user_id}")
async def send_test(user_id: int, db: Session = Depends(get_db)):
    """Send a test notification to all of a user's devices.

    Handy for verifying the whole path (subscription → encryption → SW handler)
    without waiting for a scheduled reminder.
    """
    get_user_or_404(db, user_id)
    if not push_service.push_enabled():
        raise HTTPException(status_code=503, detail="Web Push is not configured (VAPID keys unset)")
    payload = push_service.build_payload(
        title="LinguaAI",
        body="Powiadomienia działają! 🎉",
        url="/",
        tag="test",
    )
    result = push_service.send_to_user(db, user_id, payload)
    return {"success": True, **result}
