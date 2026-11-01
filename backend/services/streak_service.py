"""Streak calculation service, and the weekly day count that replaces the
streak in the UI (A8): days with a finished lesson this week, goal 5 of 7, as
the hub's Feed counts them. One missed day does not stop habit formation
(Lally et al. 2010), so nothing resets to zero.
"""
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from backend.models.lesson import Lesson
from backend.services import local_day


def calculate_streak(db: Session, user_id: int, freezes_available: int = 0) -> tuple[int, int]:
    """Calculate consecutive local days with at least one completed lesson.

    Uses streak freezes to bridge single-day gaps (1 missed day = 1 freeze).
    Returns (streak_length, freezes_remaining). A pure function of the history and
    the allowance: callers must not store freezes_remaining back as the allowance,
    because the next call counts the same old gaps again (until 01.11.2026 every
    completed lesson charged the old gaps once more and the streak broke).
    """
    rows = db.query(Lesson.completed_at).filter(
        Lesson.user_id == user_id,
        Lesson.is_completed == True,  # noqa: E712
        Lesson.completed_at != None,  # noqa: E711
    ).all()
    if not rows:
        return 0, freezes_available

    date_list = sorted({local_day.local_date(r[0]) for r in rows}, reverse=True)
    today = local_day.local_today()

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


def streak_at_date(lessons: list, target_date) -> int:
    """Count consecutive completed-lesson days ending at ``target_date``.

    Used by CSV export to show the running streak for each historical lesson
    (instead of re-implementing the heuristic inline in the stats router).
    """
    from datetime import timedelta

    completed_dates = sorted({
        local_day.local_date(l.completed_at)
        for l in lessons
        if l.completed_at and l.is_completed
    })
    if target_date not in completed_dates:
        return 0
    count = 1
    prev = target_date - timedelta(days=1)
    while prev in completed_dates:
        count += 1
        prev -= timedelta(days=1)
    return count


WEEK_GOAL_DAYS = 5  # the same goal as the hub's Feed ("5 z 7")


def week_days(db: Session, user_id: int, today: date | None = None) -> dict:
    """Days of the current week (Monday to today, local time) with a finished lesson."""
    today = today or local_day.local_today()
    monday = today - timedelta(days=today.weekday())
    since = datetime.combine(monday - timedelta(days=1), datetime.min.time())  # margin for the UTC offset
    rows = db.query(Lesson.completed_at).filter(
        Lesson.user_id == user_id,
        Lesson.is_completed == True,  # noqa: E712
        Lesson.completed_at != None,  # noqa: E711
        Lesson.completed_at >= since,
    ).all()
    dates = sorted({d for d in (local_day.local_date(r[0]) for r in rows) if monday <= d <= today})
    return {"week_start": monday.isoformat(), "days": len(dates), "goal": WEEK_GOAL_DAYS,
            "dates": [d.isoformat() for d in dates]}
