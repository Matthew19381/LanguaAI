"""Single shared-secret gate for the whole app.

This is not user accounts — it is one password for one owner, so the app can be
exposed over a tunnel or a cloud URL without leaving the API (and the AI credits
behind it) open to anyone who guesses the address.

The secret is exchanged for an HttpOnly cookie: JavaScript never holds it, and
plain ``<audio src="/audio/...">`` requests carry it automatically.
"""
import logging
import secrets
import time
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

COOKIE_NAME = "linguaai_access"
COOKIE_MAX_AGE = 60 * 60 * 24 * 180  # 180 days — this is a personal device

# Throttle brute-force on the unlock endpoint. The token has ~256 bits of entropy
# so guessing is infeasible anyway, but a lockout is cheap defense-in-depth and
# stops an attacker hammering the endpoint. Only FAILED attempts count; a correct
# unlock clears the counter for that IP.
_UNLOCK_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_UNLOCK_LOCK = Lock()
UNLOCK_MAX_ATTEMPTS = 5
UNLOCK_WINDOW_SECONDS = 300  # 5 minutes


class UnlockRequest(BaseModel):
    token: str


def gate_enabled() -> bool:
    return bool(settings.APP_ACCESS_TOKEN)


def request_is_authorized(request: Request) -> bool:
    """True when the gate is off, or the caller proved the shared secret."""
    if not gate_enabled():
        return True
    expected = settings.APP_ACCESS_TOKEN
    # compare_digest avoids leaking the secret through response timing
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie and secrets.compare_digest(cookie, expected):
        return True
    header = request.headers.get("X-App-Token")
    if header and secrets.compare_digest(header, expected):
        return True
    return False


@router.get("/api/auth/status")
async def auth_status(request: Request):
    """Whether the gate is on and whether this device is already unlocked."""
    return {
        "gate_enabled": gate_enabled(),
        "unlocked": request_is_authorized(request),
    }


@router.post("/api/auth/unlock")
async def unlock(payload: UnlockRequest, request: Request, response: Response):
    """Exchange the shared secret for a long-lived HttpOnly cookie."""
    if not gate_enabled():
        return {"success": True, "gate_enabled": False}

    ip = request.client.host if request.client else "unknown"
    now = time.time()
    with _UNLOCK_LOCK:
        recent = [t for t in _UNLOCK_ATTEMPTS[ip] if t > now - UNLOCK_WINDOW_SECONDS]
        _UNLOCK_ATTEMPTS[ip] = recent
        if len(recent) >= UNLOCK_MAX_ATTEMPTS:
            logger.warning("Unlock rate-limited for %s", ip)
            return JSONResponse(status_code=429,
                                content={"detail": "Too many attempts. Please wait and try again."})

        if not secrets.compare_digest(payload.token or "", settings.APP_ACCESS_TOKEN):
            recent.append(now)
            _UNLOCK_ATTEMPTS[ip] = recent
            logger.warning("Failed unlock attempt from %s", ip)
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        # Correct secret — clear the failed-attempt counter for this device.
        _UNLOCK_ATTEMPTS.pop(ip, None)

    response.set_cookie(
        key=COOKIE_NAME,
        value=settings.APP_ACCESS_TOKEN,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        # Set on HTTPS (tunnel/cloud); harmless to omit on plain-HTTP localhost
        secure=settings.BACKEND_URL.startswith("https"),
        path="/",
    )
    return {"success": True, "gate_enabled": True}


@router.post("/api/auth/lock")
async def lock(response: Response):
    """Forget this device."""
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"success": True}


# ── Magic-link login: bind a new device to the (single) account ──────────

@router.get("/api/v1/users/{user_id}/login-link")
def get_login_link(user_id: int, db: Session = Depends(get_db)):
    """Return (and lazily create) the magic-link token for this account.

    Single-user app: anyone holding this link can log in as the owner, so it
    is only ever shown behind the access gate on the owner's own device.
    NOTE: mounted on the auth router (no mount prefix), so the full path is used.
    """
    from backend.utils import get_user_or_404

    user = get_user_or_404(db, user_id)
    if not user.login_token:
        user.login_token = secrets.token_urlsafe(24)
        db.commit()
        db.refresh(user)
    return {"login_token": user.login_token, "user_id": user.id}


@router.get("/api/auth/magic")
def magic_login(key: str, db: Session = Depends(get_db)):
    """Resolve a magic-link key to the account it belongs to.

    The frontend route /login-as?key=... calls this, stores the returned
    userId in localStorage, and the device is bound — no typing ids by hand.
    """
    from backend.models.user import User

    if not key or len(key) < 16:
        raise HTTPException(status_code=401, detail="Invalid login key")
    user = db.query(User).filter(User.login_token == key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid login key")
    return {
        "user_id": user.id,
        "name": user.name,
        "target_language": user.target_language,
        "cefr_level": user.cefr_level,
    }
