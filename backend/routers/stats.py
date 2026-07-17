import csv
import io
import json
import logging
from datetime import date, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.test_result import TestResult
from backend.models.user import User
from backend.services.lesson_generator import generate_daily_tips
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)
router = APIRouter()


def calculate_level(xp: int) -> dict:
    """Calculate user level (1-50) using quadratic curve via achievement_service."""
    from backend.services.achievement_service import calculate_level_from_xp
    return calculate_level_from_xp(xp)


@router.get("/api/stats/{user_id}")
async def get_stats(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)

    # Get lesson stats (filter by current target language)
    all_lessons = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language
    ).all()

    # Get test history
    test_results = db.query(TestResult).filter(
        TestResult.user_id == user_id
    ).order_by(TestResult.created_at.desc()).limit(30).all()

    # Get flashcard stats
    flashcards = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.is_active == True
    ).all()

    now = datetime.now()
    due_flashcards = [f for f in flashcards if f.next_review_date and f.next_review_date <= now]

    # Calculate streaks (with freeze support)
    from backend.services.streak_service import calculate_streak
    streak, freezes_left = calculate_streak(db, user_id, user.streak_freezes)

    # Calculate error categories with examples
    error_categories = {}
    error_examples = {}  # category -> list of example errors (up to 3)
    for test in test_results:
        if test.errors:
            try:
                errors = json.loads(test.errors)
                for error in errors:
                    if isinstance(error, dict):
                        error_type = error.get("type", "unknown")
                    else:
                        error_type = str(error)
                    error_categories[error_type] = error_categories.get(error_type, 0) + 1
                    if error_type not in error_examples:
                        error_examples[error_type] = []
                    if len(error_examples[error_type]) < 3:
                        if isinstance(error, dict):
                            example = {
                                "question": error.get("question", error.get("error", "")),
                                "correct": error.get("correct_answer", error.get("correction", "")),
                            }
                        else:
                            example = {"question": str(error), "correct": ""}
                        if example["question"] and example not in error_examples[error_type]:
                            error_examples[error_type].append(example)
            except (json.JSONDecodeError, TypeError):
                pass

    # Test history for chart
    test_history_chart = []
    for result in reversed(test_results[:14]):  # Last 14 tests
        test_history_chart.append({
            "date": result.created_at.strftime("%m/%d"),
            "score": round(result.score, 1),
            "type": result.test_type
        })

    # Deduplicate by day_number — keep the latest lesson per day
    seen_days = {}
    for lesson in all_lessons:
        if lesson.day_number not in seen_days or lesson.id > seen_days[lesson.day_number].id:
            seen_days[lesson.day_number] = lesson
    unique_lessons = sorted(seen_days.values(), key=lambda x: x.day_number)

    lesson_history = []
    for lesson in unique_lessons:
        lesson_history.append({
            "id": lesson.id,
            "day": lesson.day_number,
            "title": lesson.title,
            "completed": lesson.is_completed,
            "date": lesson.created_at.strftime("%m/%d")
        })

    level_info = calculate_level(user.total_xp)

    from backend.services.achievement_service import get_all_achievements_for_user, get_unnotified_achievements
    achievements_data = get_all_achievements_for_user(user_id, db)
    unnotified = get_unnotified_achievements(user_id, db)

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "native_language": user.native_language,
            "target_language": user.target_language,
            "cefr_level": user.cefr_level,
            "streak_days": streak,
            "streak_freezes": freezes_left,
            "total_xp": user.total_xp,
            "member_since": user.created_at.strftime("%B %d, %Y") if user.created_at else "Unknown"
        },
        "level_info": level_info,
        "lessons": {
            "total": len(unique_lessons),
            "completed": len([l for l in unique_lessons if l.is_completed]),
            "completion_rate": round(len([l for l in unique_lessons if l.is_completed]) / len(unique_lessons) * 100, 1) if unique_lessons else 0,
            "history": lesson_history
        },
        "tests": {
            "total_taken": len(test_results),
            "average_score": round(sum(t.score for t in test_results) / len(test_results), 1) if test_results else 0,
            "best_score": round(max(t.score for t in test_results), 1) if test_results else 0,
            "history": test_history_chart
        },
        "flashcards": {
            "total": len(flashcards),
            "due_today": len(due_flashcards)
        },
        "error_categories": error_categories,
        "error_examples": error_examples,
        "achievements": achievements_data,
        "new_achievements": unnotified,
    }



@router.get("/api/tips/{user_id}")
async def get_daily_tips(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)

    try:
        tips = await generate_daily_tips(
            cefr_level=user.cefr_level,
            language=user.target_language,
            native_language=user.native_language
        )
        return {
            "success": True,
            "user_id": user_id,
            "cefr_level": user.cefr_level,
            "language": user.target_language,
            "tips": tips.get("tips", [])
        }
    except httpx.RequestError as e:
        logger.error(f"AI service error generating tips: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception:
        logger.exception("Unexpected error getting daily tips")
        raise HTTPException(status_code=500, detail="Failed to generate tips")


@router.get("/api/stats/{user_id}/leaderboard")
async def get_leaderboard_position(user_id: int, db: Session = Depends(get_db)):
    """Get the user's position among all users by XP."""
    user = get_user_or_404(db, user_id)

    # Get top 5 users by XP (efficient — only loads 5 rows)
    top_users = db.query(User).order_by(User.total_xp.desc()).limit(5).all()
    total_users = db.query(User).count()

    # Calculate user position efficiently via count of users with higher XP
    position = db.query(User).filter(User.total_xp > user.total_xp).count() + 1

    return {
        "user_id": user_id,
        "position": position,
        "total_users": total_users,
        "xp": user.total_xp,
        "top_users": [
            {
                "name": u.name,
                "xp": u.total_xp,
                "cefr_level": u.cefr_level
            }
            for u in top_users
        ]
    }


@router.get("/api/stats/{user_id}/export-csv")
async def export_progress_csv(user_id: int, db: Session = Depends(get_db)):
    from backend.services.streak_service import streak_at_date
    user = get_user_or_404(db, user_id)

    lessons = db.query(Lesson).filter(Lesson.user_id == user_id).order_by(Lesson.created_at.asc()).all()
    test_results = db.query(TestResult).filter(TestResult.user_id == user_id).order_by(TestResult.created_at.asc()).all()
    flashcards = db.query(Flashcard).filter(Flashcard.user_id == user_id).all()

    # Build test results lookup by date
    tests_by_date = {}
    for t in test_results:
        d = t.created_at.strftime("%Y-%m-%d")
        if d not in tests_by_date:
            tests_by_date[d] = []
        tests_by_date[d].append(round(t.score, 1))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "day_number", "lesson_title", "lesson_completed", "test_scores", "xp_total", "streak", "flashcard_count"])

    # Calculate cumulative XP and per-lesson streak using the shared streak service
    xp = 0

    for lesson in lessons:
        d = lesson.created_at.strftime("%Y-%m-%d")
        if lesson.is_completed:
            xp += 25
            lesson_streak = streak_at_date(lessons, lesson.completed_at.date()) if lesson.completed_at else 0
        else:
            lesson_streak = 0
        scores = tests_by_date.get(d, [])
        scores_str = ";".join(str(s) for s in scores) if scores else ""
        writer.writerow([
            d,
            lesson.day_number,
            lesson.title,
            lesson.is_completed,
            scores_str,
            xp,
            lesson_streak,
            len(flashcards),
        ])

    output.seek(0)
    filename = f"progress_{user.name}_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/api/stats/{user_id}/errors")
async def get_all_errors(user_id: int, db: Session = Depends(get_db)):
    """Return all test errors for the user, grouped by type, for the error review page."""
    user = get_user_or_404(db, user_id)

    test_results = db.query(TestResult).filter(
        TestResult.user_id == user_id,
        TestResult.language == user.target_language
    ).order_by(TestResult.created_at.desc()).all()

    all_errors = []
    for test in test_results:
        if not test.errors:
            continue
        try:
            errors = json.loads(test.errors)
            date_str = test.created_at.strftime("%d.%m.%Y")
            for err in errors:
                if isinstance(err, dict):
                    # Conversation errors use 'question' as the problematic phrase (user_answer)
                    user_answer = err.get("user_answer", "")
                    if not user_answer and test.test_type == "conversation":
                        user_answer = err.get("question", "")
                    all_errors.append({
                        "type": err.get("type", "unknown"),
                        "question": err.get("question", err.get("error", "")),
                        "user_answer": user_answer,
                        "correct_answer": err.get("correct_answer", err.get("correction", "")),
                        "explanation": err.get("explanation", err.get("rule", "")),
                        "practice": err.get("practice", ""),
                        "date": date_str,
                        "test_id": test.id,
                        "source": test.test_type or "test",
                    })
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    # Group by type
    grouped: dict = {}
    for err in all_errors:
        t = err["type"]
        if t not in grouped:
            grouped[t] = []
        grouped[t].append(err)

    # Sort groups by count desc
    grouped_list = [
        {"type": k, "count": len(v), "errors": v}
        for k, v in sorted(grouped.items(), key=lambda x: -len(x[1]))
    ]

    return {
        "total": len(all_errors),
        "language": user.target_language,
        "groups": grouped_list,
    }
