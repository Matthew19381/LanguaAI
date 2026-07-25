"""Pydantic schemas for the Web Push router."""
from typing import Optional

from pydantic import BaseModel


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionIn(BaseModel):
    """The shape returned by the browser's PushManager.subscribe().toJSON()."""
    endpoint: str
    keys: PushKeys


class SubscribeRequest(BaseModel):
    user_id: int
    subscription: PushSubscriptionIn


class UnsubscribeRequest(BaseModel):
    endpoint: str
    user_id: Optional[int] = None
