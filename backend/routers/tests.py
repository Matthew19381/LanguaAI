import json
import logging
import httpx
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.user import User
from backend.utils import get_user_or_404
from backend.models.lesson import Lesson
from backend.models.test_result import TestResult
from backend.schemas.test import SubmitTestRequest
from backend.services.test_generator import (
    get_or_create_daily_test,
    submit_test,
    get_or_create_weekly_test,
    get_test_history
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/tests/daily/{user_id}")
async def get_daily_test(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)

    # Find today's lesson for the user's current language
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_lesson = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language,
        Lesson.created_at >= today_start
    ).first()

    if not today_lesson:
        # Fallback: try latest lesson for this language regardless of date
        today_lesson = db.query(Lesson).filter(
            Lesson.user_id == user_id,
            Lesson.language == user.target_language
        ).order_by(Lesson.created_at.desc()).first()

    if not today_lesson:
        raise HTTPException(
            status_code=404,
            detail="Brak lekcji. Najpierw wygeneruj dzisiejszą lekcję."
        )

    lesson_content = json.loads(today_lesson.content)

    try:
        test_data = await get_or_create_daily_test(user_id, lesson_content, db)
        return {
            "success": True,
            "lesson_id": today_lesson.id,
            "lesson_title": today_lesson.title,
            **test_data
        }
    except httpx.RequestError as e:
        logger.error(f"AI service error getting daily test: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception:
        logger.exception("Unexpected error getting daily test")
        raise HTTPException(status_code=500, detail="Failed to load daily test")


@router.post("/api/tests/submit")
async def submit_test_answers(
    request: SubmitTestRequest,
    db: Session = Depends(get_db)
):
    try:
        result = await submit_test(
            user_id=request.user_id,
            test_type=request.test_type,
            questions=request.questions,
            answers=request.answers,
            db=db
        )
        # Check achievements after test
        from backend.services.achievement_service import check_and_award_achievements
        user = db.query(User).filter(User.id == request.user_id).first()
        newly_awarded = []
        if user:
            newly_awarded = check_and_award_achievements(user, db)
        return {
            "success": True,
            "new_achievements": newly_awarded,
            **result
        }
    except httpx.RequestError as e:
        logger.error(f"AI service error submitting test: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Unexpected error submitting test")
        raise HTTPException(status_code=500, detail="Failed to submit test")


@router.get("/api/tests/errors/{user_id}")
async def get_errors_test(user_id: int, db: Session = Depends(get_db)):
    """Generate a test targeting the user's past error patterns."""
    from backend.services.lesson_generator import generate_errors_test
    user = get_user_or_404(db, user_id)

    # Get recent errors from test results
    from backend.models.test_result import TestResult
    import json as _json
    test_results = db.query(TestResult).filter(
        TestResult.user_id == user_id,
        TestResult.language == user.target_language
    ).order_by(TestResult.created_at.desc()).limit(20).all()

    all_errors = []
    for test in test_results:
        if not test.errors:
            continue
        try:
            errors = _json.loads(test.errors)
            for err in errors:
                # Skip malformed (non-dict) error entries defensively
                if not isinstance(err, dict):
                    continue
                if err.get("correct_answer") or err.get("correction"):
                    all_errors.append({
                        "type": err.get("type", "unknown"),
                        "question": err.get("question", err.get("error", "")),
                        "user_answer": err.get("user_answer", ""),
                        "correct_answer": err.get("correct_answer", err.get("correction", "")),
                    })
        except (json.JSONDecodeError, TypeError):
            pass

    try:
        test_data = await generate_errors_test(
            errors=all_errors,
            cefr_level=user.cefr_level,
            language=user.target_language,
            native_language=user.native_language
        )
        return {"success": True, "test_type": "errors", **test_data}
    except httpx.RequestError as e:
        logger.error(f"AI service error generating errors test: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception:
        logger.exception("Unexpected error generating errors test")
        raise HTTPException(status_code=500, detail="Failed to generate error test")


@router.get("/api/tests/weekly/{user_id}")
async def get_weekly_test(
    user_id: int,
    week: Optional[int] = None,
    db: Session = Depends(get_db)
):
    user = get_user_or_404(db, user_id)

    if week is None:
        # Calculate current week number
        if user.created_at:
            days_elapsed = (date.today() - user.created_at.date()).days
            week = (days_elapsed // 7) + 1
        else:
            week = 1

    try:
        test_data = await get_or_create_weekly_test(user_id, week, db)
        return {
            "success": True,
            **test_data
        }
    except httpx.RequestError as e:
        logger.error(f"AI service error getting weekly test: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Unexpected error getting weekly test")
        raise HTTPException(status_code=500, detail="Failed to load weekly test")


@router.get("/api/tests/history/{user_id}")
async def get_history(
    user_id: int,
    limit: Optional[int] = 20,
    db: Session = Depends(get_db)
):
    history = get_test_history(user_id, db, limit)

    # Calculate stats
    if history:
        avg_score = sum(h["score"] for h in history) / len(history)
        best_score = max(h["score"] for h in history)
        total_tests = len(history)
    else:
        avg_score = 0
        best_score = 0
        total_tests = 0

    return {
        "history": history,
        "stats": {
            "total_tests": total_tests,
            "average_score": round(avg_score, 1),
            "best_score": round(best_score, 1)
        }
    }


@router.get("/api/tests/result/{result_id}")
async def get_test_result(result_id: int, user_id: int, db: Session = Depends(get_db)):
    result = db.query(TestResult).filter(TestResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Test result not found")

    # Verify ownership
    if result.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this test result")

    errors = json.loads(result.errors) if result.errors else []
    answers = json.loads(result.answers) if result.answers else {}

    return {
        "id": result.id,
        "user_id": result.user_id,
        "test_type": result.test_type,
        "score": result.score,
        "answers": answers,
        "errors": errors,
        "cefr_level": result.cefr_level,
        "language": result.language,
        "created_at": result.created_at.isoformat()
    }
