import asyncio
import json
import logging

from sqlalchemy.orm import Session

from backend.models.test_result import TestResult
from backend.models.user import User
from backend.services.lesson_generator import analyze_test_errors, generate_daily_test, generate_weekly_test
from backend.services.local_day import local_today, on_local_day

logger = logging.getLogger(__name__)

# One submission per user and test type at a time: the answer check takes seconds,
# and two taps used to pass the "already submitted today" check together and give XP
# twice (the unique key includes the full timestamp, so it never caught them).
_submit_locks: dict[tuple, asyncio.Lock] = {}


def _taken_today(db: Session, user, test_type: str):
    return db.query(TestResult).filter(
        TestResult.user_id == user.id,
        TestResult.test_type == test_type,
        TestResult.language == user.target_language,
        on_local_day(TestResult.created_at, local_today()),
    ).order_by(TestResult.id).first()


async def get_or_create_daily_test(
    user_id: int,
    lesson_content: dict,
    db: Session,
    lesson=None,
) -> dict:
    """Get or generate a daily test for a user.

    The generated questions are cached inside the lesson's content blob under
    ``daily_test`` so that reopening the test page does not pay for the same AI
    generation again. Pass ``lesson`` (the Lesson row) to enable that caching.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Already taken on the learner's local day (per language)
    existing_test = _taken_today(db, user, "daily")
    if existing_test:
        return {
            "test_id": existing_test.id,
            "already_taken": True,
            "score": existing_test.score,
            # Until 01.11.2026 the stored answers were returned here as "questions"
            "questions": [],
            "errors": json.loads(existing_test.errors) if existing_test.errors else [],
        }

    # Reuse the questions generated earlier for this lesson, if any
    cached = lesson_content.get("daily_test") if isinstance(lesson_content, dict) else None
    if isinstance(cached, dict) and cached.get("questions"):
        return {
            "test_id": None,
            "already_taken": False,
            "questions": cached["questions"],
            "cefr_level": user.cefr_level,
            "language": user.target_language,
            "from_cache": True,
        }

    # Generate new test from lesson content
    test_data = await generate_daily_test(
        lesson_content=lesson_content,
        cefr_level=user.cefr_level,
        language=user.target_language,
        native_language=user.native_language
    )
    questions = test_data.get("questions", [])

    # Persist into the lesson blob so the next open is free
    if lesson is not None and questions:
        try:
            content = json.loads(lesson.content) if lesson.content else {}
            content["daily_test"] = {"questions": questions}
            lesson.content = json.dumps(content, ensure_ascii=False)
            db.commit()
        except Exception as e:  # caching must never break the request
            logger.warning(f"Could not cache daily test on lesson {getattr(lesson, 'id', '?')}: {e}")
            db.rollback()

    return {
        "test_id": None,
        "already_taken": False,
        "questions": questions,
        "cefr_level": user.cefr_level,
        "language": user.target_language,
        "from_cache": False,
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

    lock = _submit_locks.setdefault((user_id, test_type), asyncio.Lock())
    async with lock:
        return await _submit(user, test_type, questions, answers, db)


def _already_submitted(existing) -> dict:
    return {
        "test_result_id": existing.id,
        "score": existing.score,
        "errors": json.loads(existing.errors) if existing.errors else [],
        "performance_summary": "",
        "xp_earned": 0,
        "already_submitted": True,
    }


async def _submit(user, test_type: str, questions: list, answers: dict, db: Session) -> dict:
    user_id = user.id
    # Check for duplicate submission (idempotency), on the learner's local day.
    # The errors test may be taken again: each round is a new set of questions.
    if test_type != "errors":
        existing_today = _taken_today(db, user, test_type)
        if existing_today:
            return _already_submitted(existing_today)
    else:
        same = db.query(TestResult).filter(
            TestResult.user_id == user_id, TestResult.test_type == "errors",
            TestResult.language == user.target_language, TestResult.answers == json.dumps(answers),
            on_local_day(TestResult.created_at, local_today()),
        ).first()
        if same:  # the same round sent twice
            return _already_submitted(same)

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

    db.commit()
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
