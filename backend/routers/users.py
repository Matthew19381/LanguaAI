from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime

from backend.database import get_db
from backend.models.user import User
from backend.utils import get_user_or_404

router = APIRouter(
    prefix="",
    tags=["users"],
)


class SleepData(BaseModel):
    quality: int  # 1-5
    date: Optional[str] = None  # ISO date string (YYYY-MM-DD)


class NeuroWeights(BaseModel):
    sleep_modulator_weight: Optional[float] = None
    time_of_day_weight: Optional[float] = None
    interleaving_bonus_weight: Optional[float] = None
    interference_penalty_weight: Optional[float] = None


class SleepSyncPayload(BaseModel):
    """Payload from an external sleep sensor (Google Fit / Apple Health)."""
    source: str  # "google_fit" | "apple_health"
    date: Optional[str] = None  # ISO date (YYYY-MM-DD)
    sleep_quality: Optional[int] = None  # 1-5 (or normalized by caller)
    sleep_score: Optional[float] = None  # 0-100 raw vendor score


def _award_sleep_achievement(db: Session, user: User) -> Optional[dict]:
    """NEURO-14: award the 'sleep_tracker' achievement once the user logs sleep >= 3 times."""
    from backend.models.achievement import Achievement
    from backend.services.achievement_service import ACHIEVEMENT_DEFS

    try:
        data = json.loads(user.sleep_data) if user.sleep_data else {}
    except (json.JSONDecodeError, TypeError):
        data = {}
    history = data.get("history", [])
    if len(history) < 3:
        return None

    existing = db.query(Achievement).filter(
        Achievement.user_id == user.id,
        Achievement.achievement_type == "sleep_tracker",
    ).first()
    if existing:
        return None

    if "sleep_tracker" not in ACHIEVEMENT_DEFS:
        return None

    ach = Achievement(
        user_id=user.id,
        achievement_type="sleep_tracker",
        unlocked_at=datetime.now(),
        notified=False,
    )
    db.add(ach)
    db.commit()
    title, description, icon = ACHIEVEMENT_DEFS["sleep_tracker"]
    return {"type": "sleep_tracker", "title": title, "description": description, "icon": icon}


@router.post("/{user_id}/sleep", status_code=status.HTTP_200_OK)
async def set_user_sleep_data(
    user_id: int,
    sleep_data: SleepData,
    db: Session = Depends(get_db),
):
    """
    Store sleep quality data for the user. (NEURO-11)
    """
    user = get_user_or_404(db, user_id)
    if not 1 <= sleep_data.quality <= 5:
        raise HTTPException(status_code=400, detail="Sleep quality must be between 1 and 5")

    data = {}
    if user.sleep_data:
        try:
            data = json.loads(user.sleep_data)
        except (json.JSONDecodeError, TypeError):
            data = {}

    if "history" not in data:
        data["history"] = []

    sleep_date = sleep_data.date if sleep_data.date else datetime.now().date().isoformat()

    data["history"].append({
        "date": sleep_date,
        "quality": sleep_data.quality
    })

    if len(data["history"]) > 30:
        data["history"] = data["history"][-30:]

    data["last_sleep_quality"] = sleep_data.quality
    data["last_sleep_date"] = sleep_date

    user.sleep_data = json.dumps(data)
    db.commit()

    achievement = _award_sleep_achievement(db, user)
    return {
        "success": True,
        "message": "Sleep data saved",
        "new_achievement": achievement,
    }


@router.get("/{user_id}/sleep", response_model=dict)
async def get_user_sleep_data(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve the user's sleep data.
    """
    user = get_user_or_404(db, user_id)
    if not user.sleep_data:
        return {"sleep_data": {}}
    try:
        data = json.loads(user.sleep_data)
    except (json.JSONDecodeError, TypeError):
        data = {}
    return {"sleep_data": data}


# ── NEURO-15: configurable neuro-FSRS weights ───────────────────────────────

@router.get("/{user_id}/neuro-weights", response_model=dict)
async def get_neuro_weights(
    user_id: int,
    db: Session = Depends(get_db),
):
    """Return the user's current neuro-FSRS weights (defaults if unset)."""
    user = get_user_or_404(db, user_id)
    try:
        weights = json.loads(user.neuro_weights) if user.neuro_weights else {}
    except (json.JSONDecodeError, TypeError):
        weights = {}
    return {"neuro_weights": weights}


@router.patch("/{user_id}/neuro-weights", response_model=dict)
async def update_neuro_weights(
    user_id: int,
    payload: NeuroWeights,
    db: Session = Depends(get_db),
):
    """Update the user's neuro-FSRS weights. Missing fields keep their current value."""
    user = get_user_or_404(db, user_id)

    try:
        weights = json.loads(user.neuro_weights) if user.neuro_weights else {}
    except (json.JSONDecodeError, TypeError):
        weights = {}

    bounds = {
        "sleep_modulator_weight": (0.0, 0.3),
        "time_of_day_weight": (0.0, 0.2),
        "interleaving_bonus_weight": (0.0, 0.1),
        "interference_penalty_weight": (0.0, 0.2),
    }

    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if key not in bounds:
            raise HTTPException(status_code=400, detail=f"Unknown weight: {key}")
        lo, hi = bounds[key]
        if not lo <= value <= hi:
            raise HTTPException(
                status_code=400,
                detail=f"{key} must be between {lo} and {hi}",
            )
        weights[key] = value

    user.neuro_weights = json.dumps(weights)
    db.commit()

    # NEURO-14: award the 'neuro_tuned' achievement on first weight customisation
    new_achievement = None
    from backend.models.achievement import Achievement
    from backend.services.achievement_service import ACHIEVEMENT_DEFS
    if "neuro_tuned" in ACHIEVEMENT_DEFS and not db.query(Achievement).filter(
        Achievement.user_id == user.id,
        Achievement.achievement_type == "neuro_tuned",
    ).first():
        ach = Achievement(
            user_id=user.id,
            achievement_type="neuro_tuned",
            unlocked_at=datetime.now(),
            notified=False,
        )
        db.add(ach)
        db.commit()
        title, description, icon = ACHIEVEMENT_DEFS["neuro_tuned"]
        new_achievement = {"type": "neuro_tuned", "title": title, "description": description, "icon": icon}

    return {"success": True, "neuro_weights": weights, "new_achievement": new_achievement}


# ── NEURO-16: sleep-sensor sync (Google Fit / Apple Health) ─────────────────

@router.post("/{user_id}/sync-sleep", status_code=status.HTTP_200_OK)
async def sync_sleep_from_sensor(
    user_id: int,
    payload: SleepSyncPayload,
    db: Session = Depends(get_db),
):
    """
    Ingest a sleep record pushed from an external sensor (Google Fit / Apple Health).
    The vendor raw score is normalised to the internal 1-5 quality scale.

    NOTE: This endpoint is the integration point for NEURO-16. Real OAuth
    token exchange with Google Fit / Apple Health should happen in a background
    job (see backend/services/sleep_sensor_service.py); here we accept a
    pre-normalised payload so the data path is testable end-to-end.
    """
    user = get_user_or_404(db, user_id)

    # Normalise to 1-5 quality
    quality = payload.sleep_quality
    if quality is None and payload.sleep_score is not None:
        # 0-100 vendor score → 1-5
        quality = max(1, min(5, round(payload.sleep_score / 20.0)))

    if quality is None:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'sleep_quality' (1-5) or 'sleep_score' (0-100)",
        )
    if not 1 <= quality <= 5:
        raise HTTPException(status_code=400, detail="Normalised sleep quality must be between 1 and 5")

    data = {}
    if user.sleep_data:
        try:
            data = json.loads(user.sleep_data)
        except (json.JSONDecodeError, TypeError):
            data = {}
    if "history" not in data:
        data["history"] = []

    sleep_date = payload.date if payload.date else datetime.now().date().isoformat()
    data["history"].append({
        "date": sleep_date,
        "quality": quality,
        "source": payload.source,
    })
    if len(data["history"]) > 30:
        data["history"] = data["history"][-30:]

    data["last_sleep_quality"] = quality
    data["last_sleep_date"] = sleep_date
    if "sources" not in data:
        data["sources"] = []
    if payload.source not in data["sources"]:
        data["sources"].append(payload.source)

    user.sleep_data = json.dumps(data)
    db.commit()

    achievement = _award_sleep_achievement(db, user)
    return {
        "success": True,
        "message": f"Sleep synced from {payload.source}",
        "quality": quality,
        "new_achievement": achievement,
    }
