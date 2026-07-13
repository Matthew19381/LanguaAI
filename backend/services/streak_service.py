"""Streak calculation service."""
from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.lesson import Lesson


def _parse_date(val):
    """Convert a date value from SQLite (string) or Python date to date object."""
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        return datetime.strptime(val, "%Y-%m-%d").date()
    return val


def calculate_streak(db: Session, user_id: int, freezes_available: int = 0) -> tuple[int, int]:
    """Calculate consecutive days with at least one completed lesson.

    Uses streak freezes to bridge single-day gaps (1 missed day = 1 freeze).
    Returns (streak_length, freezes_remaining).
    """
    dates = db.query(func.date(Lesson.completed_at)).filter(
        Lesson.user_id == user_id,
        Lesson.is_completed == True,
        Lesson.completed_at != None,
    ).distinct().order_by(func.date(Lesson.completed_at).desc()).all()

    if not dates:
        return 0, freezes_available

    date_list = [_parse_date(d[0]) for d in dates]
    today = date.today()

    # Count freezes needed to connect today to the most recent lesson
    freezes_used = 0
    gap_to_today = (today - date_list[0]).days
    if gap_to_today > 1:
        needed = gap_to_today - 1
        if needed > freezes_available:
            return 0, freezes_available
        freezes_used = needed

    # Count consecutive days backwards, using freezes for gaps
    streak = 1
    remaining_freezes = freezes_available - freezes_used
    for i in range(1, len(date_list)):
        gap = (date_list[i - 1] - date_list[i]).days
        if gap == 1:
            streak += 1
        elif gap == 2 and remaining_freezes > 0:
            remaining_freezes -= 1
            streak += 2
        else:
            break

    return streak, remaining_freezes
