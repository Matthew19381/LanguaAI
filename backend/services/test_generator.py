import json
import logging
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.test_result import TestResult
from backend.models.user import User
from backend.services.lesson_generator import analyze_test_errors, generate_daily_test, generate_weekly_test

logger = logging.getLogger(__name__)


async def get_or_create_daily_test(user_id: int, lesson_content: dict, db: Session) -> dict:
    """Get or generate a daily test for a user."""
    from datetime import date

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Check if there's already a daily test for today (per language, UTC)
    today_date = date.today()
    existing_test = db.query(TestResult).filter(
        TestResult.user_id == user_id,
        TestResult.test_type == "daily",
        TestResult.language == user.target_language,
        func.date(TestResult.created_at) == today_date
    ).first()

    if existing_test:
        return {
            "test_id": existing_test.id,
            "already_taken": True,
            "score": existing_test.score,
            "questions": json.loads(existing_test.answers) if existing_test.answers else []
        }

    # Generate new test from lesson content
    test_data = await generate_daily_test(
        lesson_content=lesson_content,
        cefr_level=user.cefr_level,
        language=user.target_language,
        native_language=user.native_language
    )

    return {
        "test_id": None,
        "already_taken": False,
        "questions": test_data.get("questions", []),
        "cefr_level": user.cefr_level,
        "language": user.target_language
    }


async def submit_test(
    user_id: int,
    test_type: str,
    questions: list,
    answers: dict,
    db: Session
) -> dict:
    """Submit test answers, analyze errors, save to DB, return results."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Check for duplicate submission (idempotency)
    today_date = date.today()
    existing_today = db.query(TestResult).filter(
        TestResult.user_id == user_id,
        TestResult.test_type == test_type,
        TestResult.language == user.target_language,
        func.date(TestResult.created_at) == today_date
    ).first()
    if existing_today:
        return {
            "test_result_id": existing_today.id,
            "score": existing_today.score,
            "errors": json.loads(existing_today.errors) if existing_today.errors else [],
            "performance_summary": "",
            "xp_earned": 0,
            "already_submitted": True
        }

    # Analyze errors
    analysis = await analyze_test_errors(
        questions=questions,
        answers=answers,
        language=user.target_language,
        native_language=user.native_language
    )

    score = analysis.get("score", 0)
    # Validate score range
    score = max(0.0, min(100.0, float(score)))
    errors = analysis.get("errors", [])

    # Save test result to DB
    test_result = TestResult(
        user_id=user_id,
        test_type=test_type,
        score=score,
        answers=json.dumps(answers),
        errors=json.dumps(errors),
        cefr_level=user.cefr_level,
        language=user.target_language
    )
    db.add(test_result)

    # Award XP based on score (max 50 XP per test)
    xp_earned = min(50, int(score * 0.5))
    user.total_xp += xp_earned

    try:
        db.commit()
    except Exception:  # intentional: any DB error during concurrent test submission
        # Handle race condition: unique constraint violation means another request
        # already submitted — rollback and return the existing result
        db.rollback()
        existing = db.query(TestResult).filter(
            TestResult.user_id == user_id,
            TestResult.test_type == test_type,
            TestResult.language == user.target_language,
            func.date(TestResult.created_at) == today_date
        ).first()
        if existing:
            return {
                "test_result_id": existing.id,
                "score": existing.score,
                "errors": json.loads(existing.errors) if existing.errors else [],
                "performance_summary": "",
                "xp_earned": 0,
                "already_submitted": True
            }
        raise
    db.refresh(test_result)

    return {
        "test_result_id": test_result.id,
        "score": score,
        "errors": errors,
        "performance_summary": analysis.get("performance_summary", ""),
        "xp_earned": xp_earned
    }


async def get_or_create_weekly_test(user_id: int, week_number: int, db: Session) -> dict:
    """Get or generate a weekly test."""
    from backend.models.study_plan import StudyPlan

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Get active study plan
    study_plan = db.query(StudyPlan).filter(
        StudyPlan.user_id == user_id,
        StudyPlan.is_active == True
    ).first()

    if not study_plan:
        raise ValueError("No active study plan found")

    study_plan_data = json.loads(study_plan.plan_data)

    # Generate weekly test
    test_data = await generate_weekly_test(
        study_plan_data=study_plan_data,
        week_number=week_number,
        cefr_level=user.cefr_level,
        language=user.target_language,
        native_language=user.native_language
    )

    return {
        "week_number": week_number,
        "questions": test_data.get("questions", []),
        "cefr_level": user.cefr_level,
        "language": user.target_language
    }


def calculate_score(questions: list, answers: dict) -> float:
    """Calculate test score from questions and answers."""
    total_points = sum(q.get("points", 10) for q in questions)
    if total_points == 0:
        return 0.0

    earned_points = 0
    for q in questions:
        user_ans = answers.get(str(q["id"]), answers.get(q["id"], ""))
        if str(user_ans).upper().strip() == str(q["correct"]).upper().strip():
            earned_points += q.get("points", 10)

    return (earned_points / total_points) * 100


def get_test_history(user_id: int, db: Session, limit: int = 20) -> list:
    """Get test history for a user."""
    results = db.query(TestResult).filter(
        TestResult.user_id == user_id
    ).order_by(TestResult.created_at.desc()).limit(limit).all()

    history = []
    for result in results:
        history.append({
            "id": result.id,
            "test_type": result.test_type,
            "score": result.score,
            "cefr_level": result.cefr_level,
            "created_at": result.created_at.isoformat(),
            "errors_count": len(json.loads(result.errors)) if result.errors else 0
        })

    return history
