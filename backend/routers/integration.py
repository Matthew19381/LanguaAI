"""INT-1: ecosystem summary endpoint for System-Glowny.

System-Glowny polls GET /api/v1/summary?user_id=&date= and expects the unified
format: {module, user_id, date, summary, events, wellbeing_contribution}.
Read-only aggregation over existing tables — no writes, no AI calls.

suggested_items (contract 1.1a) puts today's lesson into the hub's day plan;
the hub ticks it itself when LinguaAI publishes lesson_completed
(services/hub_events.py).

wellbeing_contribution is intentionally null: an honest value needs the
Affect Engine (MASTER_PLAN F2-4); activity counts alone are not wellbeing.
"""
from datetime import date as date_type
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.test_result import TestResult
from backend.models.user import User
from backend.services.curriculum import DAY_TYPE_PL
from backend.services.plan_day import as_dict, current_plan_day
from backend.services.streak_service import calculate_streak

router = APIRouter(prefix="/api/v1", tags=["Integration"])

MODULE_NAME = "lingua-ai"
# Raw estimate for one daily lesson; the hub corrects it with the user's own
# planned/actual ratio (F1-2), so this is a starting point, not a measurement.
LESSON_MINUTES = 30


def _parse_date(raw: str | None) -> date_type:
    if not raw:
        return datetime.utcnow().date()
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD")


@router.get("/summary")
def get_ecosystem_summary(
    user_id: int = Query(..., description="LinguaAI user id"),
    date: str | None = Query(None, description="YYYY-MM-DD (default: today, UTC)"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    target = _parse_date(date)
    target_iso = target.isoformat()

    lessons_completed = (
        db.query(Lesson)
        .filter(
            Lesson.user_id == user_id,
            Lesson.is_completed == True,  # noqa: E712
            func.date(Lesson.completed_at) == target_iso,
        )
        .all()
    )

    tests_submitted = (
        db.query(TestResult)
        .filter(
            TestResult.user_id == user_id,
            func.date(TestResult.created_at) == target_iso,
        )
        .all()
    )

    # Cards whose last review landed on the target date. Undercounts a card
    # reviewed twice the same day (only last_review_date is stored) — good
    # enough for a daily activity signal; per-review logging is a later step.
    reviews_done = (
        db.query(func.count(Flashcard.id))
        .filter(
            Flashcard.user_id == user_id,
            Flashcard.is_active == True,  # noqa: E712
            func.date(Flashcard.last_review_date) == target_iso,
        )
        .scalar()
        or 0
    )

    due_reviews = (
        db.query(func.count(Flashcard.id))
        .filter(
            Flashcard.user_id == user_id,
            Flashcard.is_active == True,  # noqa: E712
            func.date(Flashcard.next_review_date) <= target_iso,
        )
        .scalar()
        or 0
    )

    mastered_words = (
        db.query(func.count(Flashcard.id))
        .filter(
            Flashcard.user_id == user_id,
            Flashcard.is_active == True,  # noqa: E712
            Flashcard.is_mastered == True,  # noqa: E712
        )
        .scalar()
        or 0
    )

    streak, _freezes_left = calculate_streak(db, user_id, user.streak_freezes or 0)

    events = []
    for lesson in lessons_completed:
        events.append(
            {
                "event_type": "lesson_completed",
                "module": MODULE_NAME,
                "user_id": str(user_id),
                "timestamp": lesson.completed_at.isoformat() if lesson.completed_at else None,
                "data": {
                    "lesson_id": lesson.id,
                    "topic": lesson.topic,
                    "language": lesson.language,
                    "cefr_level": lesson.cefr_level,
                },
                "tags": ["learning"],
            }
        )
    for result in tests_submitted:
        events.append(
            {
                "event_type": "test_submitted",
                "module": MODULE_NAME,
                "user_id": str(user_id),
                "timestamp": result.created_at.isoformat() if result.created_at else None,
                "score": result.score,
                "data": {
                    "test_type": result.test_type,
                    "language": result.language,
                    "cefr_level": result.cefr_level,
                },
                "tags": ["learning", "assessment"],
            }
        )

    suggested_items = _suggested_items(db, user, target, bool(lessons_completed))

    return {
        "module": MODULE_NAME,
        "user_id": str(user_id),
        "date": target_iso,
        "summary": {
            "lessons_completed": len(lessons_completed),
            "tests_submitted": len(tests_submitted),
            "reviews_done": reviews_done,
            "due_reviews": due_reviews,
            "mastered_words": mastered_words,
            "streak": streak,
            "total_xp": user.total_xp or 0,
            "target_language": user.target_language,
            "cefr_level": user.cefr_level,
            "suggested_items": suggested_items,
        },
        "events": events,
        "wellbeing_contribution": None,
    }



def _lesson_item(day_number: int, title: str, day_type: str | None) -> dict:
    kind = DAY_TYPE_PL.get(day_type or "")
    label = f"LinguaAI: lekcja dnia {day_number}" + (f" ({kind})" if kind else "")
    theme = title.split(":", 1)[1].strip() if title.startswith("Dzień") and ":" in title else title
    return {
        "title": f"{label}: {theme}" if theme else label,
        "estimated_minutes": LESSON_MINUTES,
        "priority": 1,
        "complete_on": ["lesson_completed"],
        "includes_due_reviews": False,  # flashcards are scheduled in the hub's own deck
    }


def _suggested_items(db: Session, user: User, target: date_type, done_today: bool) -> list[dict]:
    """Today's lesson for the hub's day plan (services/plan_day.py). Nothing when a
    lesson was already finished that day or there is no active plan."""
    # The hub asks with its local date, which can be a day ahead of UTC just
    # after midnight; older dates are history, nothing to plan there.
    if done_today or target < datetime.utcnow().date() - timedelta(days=1):
        return []
    day = current_plan_day(db, user, target)
    if day is None:
        return []
    lesson = day["lesson"]
    if lesson is not None:
        if lesson.is_completed:
            return []
        return [_lesson_item(lesson.day_number, lesson.title or "", as_dict(lesson.content).get("day_type"))]
    entry = day["entry"]
    return [_lesson_item(day["day_number"], entry.get("vocabulary_theme") or "", entry.get("day_type"))]
