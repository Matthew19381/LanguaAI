"""Which day of the study plan the learner is on today.

Shared by the hub's day-plan item (routers/integration.py) and the module task
in "Rozmowa" (routers/conversation.py), so both point at the same lesson as
"Lekcja dnia" (GET /api/lessons/today): the lesson already waiting there, else
the next day of the active plan.
"""
import json
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.lesson import Lesson
from backend.models.study_plan import StudyPlan
from backend.models.user import User
from backend.services.lesson_generator.daily_lesson import plan_entry_for_day


def as_dict(raw) -> dict:
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def current_plan_day(db: Session, user: User, today: Optional[date] = None) -> Optional[dict]:
    """{"day_number", "entry", "lesson"} for today, or None without an active plan.

    ``entry`` is the plan's ``daily_topics`` item for that day ({} past the plan's
    end); ``lesson`` is the Lesson row already generated for it, if any (it may be
    completed when today's lesson is done).
    """
    plan = db.query(StudyPlan).filter(
        StudyPlan.user_id == user.id, StudyPlan.is_active == True,  # noqa: E712
    ).first()
    if not plan:
        return None
    today = today or datetime.now(timezone.utc).date()
    language = user.target_language
    lesson = db.query(Lesson).filter(
        Lesson.user_id == user.id, Lesson.language == language,
        func.date(Lesson.created_at) == today.isoformat(),
    ).order_by(Lesson.id).first() or db.query(Lesson).filter(
        Lesson.user_id == user.id, Lesson.language == language,
        Lesson.is_completed == False,  # noqa: E712
    ).order_by(Lesson.created_at.desc()).first()
    if lesson:
        day_number = lesson.day_number
    else:
        day_number = (db.query(func.count(Lesson.id)).filter(
            Lesson.user_id == user.id, Lesson.language == language,
            Lesson.is_completed == True,  # noqa: E712
        ).scalar() or 0) + 1
    entry = plan_entry_for_day(as_dict(plan.plan_data), day_number) or {}
    return {"day_number": day_number, "entry": entry, "lesson": lesson}
