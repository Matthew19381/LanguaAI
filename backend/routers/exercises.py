"""Exercise bank API — reuse generated exercises instead of regenerating them."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.exercise import Exercise
from backend.schemas.exercise import AnswerExerciseRequest, GenerateVariantsRequest
from backend.services.exercise_service import (
    build_practice_set,
    find_weak_skills,
    grade_answer,
    review_exercise,
    serialize_exercise,
)
from backend.services.lesson_generator import generate_exercise_variants
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/exercises/{user_id}/practice")
async def get_practice_set(
    user_id: int,
    size: int = 10,
    topic: str | None = None,
    db: Session = Depends(get_db),
):
    """Mixed practice set: items due for spaced retrieval + interleaved from other topics."""
    user = get_user_or_404(db, user_id)
    size = max(1, min(size, 50))
    result = build_practice_set(
        db, user_id, user.target_language, size=size, current_topic=topic
    )
    result["user_id"] = user_id
    result["language"] = user.target_language
    return result


@router.get("/api/exercises/{user_id}/stats")
async def get_exercise_stats(user_id: int, db: Session = Depends(get_db)):
    """Bank size, how many are due, and which skills look weak."""
    user = get_user_or_404(db, user_id)
    now = datetime.now(timezone.utc)
    base = db.query(Exercise).filter(
        Exercise.user_id == user_id,
        Exercise.language == user.target_language,
        Exercise.is_active == True,  # noqa: E712
    )
    total = base.count()
    due = base.filter(Exercise.next_review_date <= now).count()
    practised = base.filter(Exercise.times_seen > 0).count()
    return {
        "user_id": user_id,
        "total": total,
        "due": due,
        "practised": practised,
        "weak_skills": find_weak_skills(db, user_id, user.target_language),
    }


@router.post("/api/exercises/{exercise_id}/answer")
async def answer_exercise(
    exercise_id: int,
    request: AnswerExerciseRequest,
    db: Session = Depends(get_db),
):
    """Grade an answer, schedule the item with FSRS, and reveal the solution."""
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    if exercise.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to answer this exercise")

    correct = grade_answer(exercise.answer, request.answer)
    rating = request.rating if request.rating in (1, 2, 3, 4) else (3 if correct else 1)

    scheduling = review_exercise(db, exercise, rating)
    db.commit()

    return {
        "success": True,
        "correct": correct,
        "expected_answer": exercise.answer,
        "feedback": exercise.feedback,
        "skill_tag": exercise.skill_tag,
        **scheduling,
    }


@router.post("/api/exercises/{user_id}/generate-variants")
async def generate_variants(
    user_id: int,
    payload: GenerateVariantsRequest,
    db: Session = Depends(get_db),
):
    """Generate fresh exercises for weak skills and add them to the bank.

    This is the only path that spends an AI call — everything else reuses the bank.
    """
    user = get_user_or_404(db, user_id)
    skills = payload.skills or find_weak_skills(db, user_id, user.target_language)
    if not skills:
        return {"success": True, "added": 0, "skills": [], "message": "No weak skills to target"}

    # Avoid regenerating prompts the learner already has for these skills
    existing = db.query(Exercise.prompt).filter(
        Exercise.user_id == user_id,
        Exercise.language == user.target_language,
        Exercise.skill_tag.in_(skills),
    ).limit(15).all()

    variants = await generate_exercise_variants(
        skill_tags=skills,
        target_language=user.target_language,
        native_language=user.native_language,
        cefr_level=user.cefr_level,
        per_skill=max(1, min(payload.per_skill, 5)),
        avoid_prompts=[row[0] for row in existing],
    )

    added = []
    for v in variants:
        ex = Exercise(
            user_id=user_id,
            language=user.target_language,
            cefr_level=user.cefr_level,
            exercise_type=v.get("exercise_type"),
            instruction=v.get("instruction"),
            prompt=v["prompt"],
            answer=v["answer"],
            feedback=v.get("feedback"),
            skill_tag=v.get("skill_tag"),
            topic=None,
        )
        db.add(ex)
        added.append(ex)
    db.commit()

    return {
        "success": True,
        "added": len(added),
        "skills": skills,
        "exercises": [serialize_exercise(e) for e in added],
    }
