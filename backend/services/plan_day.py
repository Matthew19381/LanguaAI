"""Which day of the study plan the learner is on today.

Shared by the hub's day-plan item (routers/integration.py) and the module task
in "Rozmowa" (routers/conversation.py), so both point at the same lesson as
"Lekcja dnia" (GET /api/lessons/today): the lesson already waiting there, else
the next day of the active plan.
"""
import json
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.lesson import Lesson
from backend.models.study_plan import StudyPlan
from backend.models.user import User
from backend.services.local_day import local_today, on_local_day
from backend.services.lesson_generator.daily_lesson import plan_entry_for_day


def as_dict(raw) -> dict:
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def todays_lesson(db: Session, user: User, today: Optional[date] = None) -> Optional[Lesson]:
    """"Lekcja dnia": the lesson finished on the learner's local day, else the earliest
    unfinished lesson, else None (a new one is due).

    Until 01.11.2026 the lesson *created* today (UTC) came first. The next lesson is
    prepared right after one is finished (A10), so after finishing lesson N the page
    and the daily test showed lesson N+1 the same day, and N+1 counted as "today's".
    """
    today = today or local_today()
    language = user.target_language
    done = db.query(Lesson).filter(
        Lesson.user_id == user.id, Lesson.language == language,
        Lesson.is_completed == True,  # noqa: E712
        on_local_day(Lesson.completed_at, today),
    ).order_by(Lesson.completed_at.desc()).first()
    return done or current_lesson(db, user)


def current_lesson(db: Session, user: User) -> Optional[Lesson]:
    """The earliest unfinished lesson in the learner's language (plan order)."""
    return db.query(Lesson).filter(
        Lesson.user_id == user.id, Lesson.language == user.target_language,
        Lesson.is_completed == False,  # noqa: E712
    ).order_by(Lesson.day_number, Lesson.id).first()


def last_finished_lesson(db: Session, user: User) -> Optional[Lesson]:
    return db.query(Lesson).filter(
        Lesson.user_id == user.id, Lesson.language == user.target_language,
        Lesson.is_completed == True,  # noqa: E712
    ).order_by(Lesson.completed_at.desc(), Lesson.id.desc()).first()


def lesson_for_review(db: Session, user: User) -> Optional[Lesson]:
    """The lesson the daily test and the grammar concepts are about: the last finished
    one, else the current one (until 01.11.2026 the newest lesson, which after A10 is
    the prepared, not yet studied lesson)."""
    return last_finished_lesson(db, user) or current_lesson(db, user)


def next_day_number(db: Session, user: User, language: Optional[str] = None) -> int:
    """Day number of a newly generated lesson: one past the highest existing day.

    The old count of finished lessons + 1 collided with an existing day when a day had
    been skipped, and the unique key then returned that old lesson again every time.
    """
    top = db.query(func.max(Lesson.day_number)).filter(
        Lesson.user_id == user.id, Lesson.language == (language or user.target_language),
    ).scalar()
    return (top or 0) + 1


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
    lesson = todays_lesson(db, user, today)
    day_number = lesson.day_number if lesson else next_day_number(db, user)
    entry = plan_entry_for_day(as_dict(plan.plan_data), day_number) or {}
    return {"day_number": day_number, "entry": entry, "lesson": lesson}
