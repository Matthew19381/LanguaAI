"""Exercise bank API — reuse generated exercises instead of regenerating them."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.exercise import Exercise
from backend.models.sync_event import SyncEvent
from backend.schemas.exercise import AnswerExerciseRequest, GenerateVariantsRequest
from backend.services.exercise_service import (
    VARIANT_AFTER_TIMES_SEEN,
    build_practice_set,
    find_weak_skills,
    grade_answer,
    review_exercise,
    serialize_exercise,
)


def _parse_occurred_at(raw: str | None) -> datetime:
    """Parse a client timestamp, falling back to now. Never trusts the future."""
    now = datetime.now(timezone.utc)
    if not raw:
        return now
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return now
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    # A device clock running ahead must not push reviews into the future
    return min(parsed, now)
from backend.services.lesson_generator import generate_exercise_variants
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)
router = APIRouter()


async def _generate_and_store_variants(db: Session, user, skills: list[str], per_skill: int):
    """Generate fresh variants for the given skills and persist them in the bank."""
    existing = db.query(Exercise.prompt).filter(
        Exercise.user_id == user.id,
        Exercise.language == user.target_language,
        Exercise.skill_tag.in_(skills),
    ).limit(15).all()

    variants = await generate_exercise_variants(
        skill_tags=skills,
        target_language=user.target_language,
        native_language=user.native_language,
        cefr_level=user.cefr_level,
        per_skill=per_skill,
        avoid_prompts=[row[0] for row in existing],
    )

    added = []
    for v in variants:
        ex = Exercise(
            user_id=user.id,
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
    if added:
        db.commit()
    return added


@router.get("/api/exercises/{user_id}/practice")
async def get_practice_set(
    user_id: int,
    size: int = 10,
    topic: str | None = None,
    include_new: bool = False,
    db: Session = Depends(get_db),
):
    """Mixed practice set: items due for spaced retrieval + interleaved from other topics.

    With ``include_new=true`` the set is topped up with freshly generated variants
    for the learner's weak skills when the bank cannot fill it. That is the only
    branch here that spends an AI call, so it is opt-in.
    """
    user = get_user_or_404(db, user_id)
    size = max(1, min(size, 50))
    result = build_practice_set(
        db, user_id, user.target_language, size=size, current_topic=topic
    )

    result["generated_new"] = 0
    missing = size - len(result["exercises"])
    if include_new and missing > 0 and result["weak_skills"]:
        added = await _generate_and_store_variants(
            db, user, result["weak_skills"], per_skill=max(1, min(missing, 3))
        )
        if added:
            result["exercises"].extend(serialize_exercise(e) for e in added[:missing])
            result["generated_new"] = len(added[:missing])

    result["user_id"] = user_id
    result["language"] = user.target_language
    return result


@router.get("/api/exercises/{user_id}/offline-pack")
async def get_offline_pack(user_id: int, size: int = 40, db: Session = Depends(get_db)):
    """Exercises to practise without a network — **including their answers**.

    The regular /practice payload withholds answers so they cannot be read off
    the wire. Offline practice has to grade on the device, so this endpoint
    deliberately ships answers and feedback. It is opt-in and separate precisely
    so the distinction stays visible.
    """
    user = get_user_or_404(db, user_id)
    size = max(1, min(size, 200))

    rows = db.query(Exercise).filter(
        Exercise.user_id == user_id,
        Exercise.language == user.target_language,
        Exercise.is_active == True,  # noqa: E712
    ).order_by(Exercise.next_review_date.asc()).limit(size).all()

    return {
        "user_id": user_id,
        "language": user.target_language,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exercises": [
            {
                **serialize_exercise(ex, include_answer=True),
                "next_review_date": ex.next_review_date.isoformat() if ex.next_review_date else None,
            }
            for ex in rows
        ],
    }


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

    base = {
        "success": True,
        "correct": correct,
        "expected_answer": exercise.answer,
        "feedback": exercise.feedback,
        "skill_tag": exercise.skill_tag,
    }

    # ── Offline replay: the same queued answer must never count twice ──
    if request.client_event_id:
        already = db.query(SyncEvent).filter(
            SyncEvent.client_event_id == request.client_event_id
        ).first()
        if already:
            return {
                **base,
                "duplicate": True,
                "times_seen": exercise.times_seen,
                "times_correct": exercise.times_correct,
                "interval_days": exercise.interval_days,
                "state": exercise.fsrs_state,
                "next_review": exercise.next_review_date.isoformat() if exercise.next_review_date else None,
                "needs_variant": (exercise.times_seen or 0) >= VARIANT_AFTER_TIMES_SEEN,
            }

    occurred_at = _parse_occurred_at(request.answered_at)
    scheduling = review_exercise(db, exercise, rating, now=occurred_at)

    if request.client_event_id:
        db.add(SyncEvent(
            client_event_id=request.client_event_id,
            user_id=request.user_id,
            kind="exercise_answer",
            target_id=exercise.id,
            occurred_at=occurred_at,
        ))

    try:
        db.commit()
    except IntegrityError:
        # Two replays raced on the same client_event_id — the other one won.
        db.rollback()
        return {**base, "duplicate": True}

    return {**base, "duplicate": False, **scheduling}


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

    added = await _generate_and_store_variants(
        db, user, skills, per_skill=max(1, min(payload.per_skill, 5))
    )

    return {
        "success": True,
        "added": len(added),
        "skills": skills,
        "exercises": [serialize_exercise(e) for e in added],
    }
