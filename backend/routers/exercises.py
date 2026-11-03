"""Exercise bank API — reuse generated exercises instead of regenerating them."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.exercise import Exercise
from backend.models.user import User
from backend.schemas.exercise import AnswerExerciseRequest, GenerateVariantsRequest
from backend.schemas.flashcard import HubReviewRequest
from backend.services.curriculum import find_skill_id, skill_name
from backend.services.exercise_service import (
    AUTO_VARIANT_FRESH_TARGET,
    VARIANT_AFTER_TIMES_SEEN,
    build_practice_set,
    find_weak_skills,
    grade_answer,
    needs_model_check,
    review_exercise,
    serialize_exercise,
    skill_memorized_needs_variant,
    skill_needs_auto_variant,
    skill_practice_set,
)
from backend.services.lesson_generator import generate_exercise_variants
from backend.services.lesson_generator.answers import grade_open_answers
from backend.services.mastery import (
    MASTERY_ACCURACY,
    MASTERY_DAYS,
    MIN_ATTEMPTS,
    WINDOW,
    record_attempt,
    skill_mastery,
)
from backend.services.sync_service import already_applied, parse_occurred_at, record_event
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
            skill_id=find_skill_id(v.get("skill_tag")),
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
    skill: str | None = None,
    db: Session = Depends(get_db),
):
    """Mixed practice set: items due for spaced retrieval + interleaved from other topics.

    With ``include_new=true`` the set is topped up with freshly generated variants
    for the learner's weak skills when the bank cannot fill it. That is the only
    branch here that spends an AI call, so it is opt-in.
    """
    user = get_user_or_404(db, user_id)
    size = max(1, min(size, 50))
    if skill:   # one Bank wiedzy skill (3.11.2026)
        result = skill_practice_set(db, user_id, user.target_language, skill, size=size)
        result.update(generated_new=0, user_id=user_id, language=user.target_language)
        return result
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
    graded_by_model = False
    # An own sentence or translation can be right in other words than the sample
    # (3.11.2026). Only a live answer is sent to the model: a queued offline answer
    # (answered_at set) keeps the device's result, so a reconnect spends nothing.
    if (not correct and request.answered_at is None and request.rating is None
            and request.answer.strip() and needs_model_check(exercise.exercise_type, exercise.answer)):
        user = db.get(User, request.user_id)
        task = ": ".join(x for x in (exercise.instruction, exercise.prompt) if x)
        verdicts = await grade_open_answers(
            [{"id": exercise.id, "type": exercise.exercise_type or "translation", "question": task,
              "expected": exercise.answer, "answer": request.answer}],
            exercise.language, (user.native_language if user else None) or "Polish")
        if verdicts.get(str(exercise.id)) is True:
            correct = graded_by_model = True
    rating = request.rating if request.rating in (1, 2, 3, 4) else (3 if correct else 1)

    base = {
        "success": True,
        "correct": correct,
        "expected_answer": exercise.answer,
        "feedback": exercise.feedback,
        "skill_tag": exercise.skill_tag,
        "graded_by_model": graded_by_model,
    }

    # ── Offline replay: the same queued answer must never count twice ──
    if already_applied(db, request.client_event_id):
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

    occurred_at = parse_occurred_at(request.answered_at)
    last = exercise.last_review_date
    if last is not None and (last if last.tzinfo else last.replace(tzinfo=timezone.utc)) > occurred_at:
        # A queued offline answer older than the item's last review (e.g. one from the hub):
        # the newer review wins, as for flashcards (until 01.11.2026 it overwrote it)
        raise HTTPException(status_code=409, detail="Exercise has a newer review")
    scheduling = review_exercise(db, exercise, rating, now=occurred_at)
    record_event(db, request.client_event_id, request.user_id,
                 "exercise_answer", exercise.id, occurred_at)
    # Per-skill log for mastery; counts as correct like the counters do (rating >= 3)
    record_attempt(
        db, user_id=request.user_id, language=exercise.language,
        skill_id=exercise.skill_id or find_skill_id(exercise.skill_tag), source="exercise",
        correct=rating >= 3, occurred_at=occurred_at, exercise_id=exercise.id,
        detail=None if rating >= 3 else {
            "prompt": exercise.prompt, "wrong": request.answer, "correct": exercise.answer},
    )

    try:
        db.commit()
    except IntegrityError:
        # Two replays raced on the same client_event_id — the other one won.
        db.rollback()
        return {**base, "duplicate": True}

    result = {**base, "duplicate": False, **scheduling}

    # ── Track first-attempt incorrect answers for FSRS ──
    if exercise.times_seen == 1 and rating < 3:  # First attempt and incorrect
        exercise.first_attempt_incorrect = True
        exercise.first_attempt_incorrect_date = occurred_at
        db.commit()
        result["first_attempt_incorrect"] = True
        result["first_attempt_incorrect_date"] = occurred_at.isoformat()

    # ── Auto-generate fresh variants when the skill needs new surface forms ──
    # Two triggers, both bounded by the shared fresh-variant guard and surfaced
    # in the response so the "AI spend is deliberate and visible" contract holds
    # without a click:
    #   • struggle  — a wrong answer on a skill the learner keeps failing
    #   • mastery   — a correct answer on an item seen so often it may be memorised
    #                 (recalling the answer, not the rule) → practise it anew
    # Only on a live answer: a replayed offline answer (client_event_id set) must
    # not spend AI on reconnect and could arrive as a burst.
    reason = None
    if request.client_event_id is None and exercise.skill_tag:
        if not correct and skill_needs_auto_variant(
            db, request.user_id, exercise.language, exercise.skill_tag
        ):
            reason = "struggle"
        elif correct and skill_memorized_needs_variant(
            db, request.user_id, exercise.language, exercise.skill_tag, exercise.times_seen
        ):
            reason = "mastery"

    if reason:
        try:
            user = get_user_or_404(db, request.user_id)
            added = await _generate_and_store_variants(
                db, user, [exercise.skill_tag], per_skill=AUTO_VARIANT_FRESH_TARGET
            )
            if added:
                result["auto_generated"] = len(added)
                result["auto_generated_skill"] = exercise.skill_tag
                result["auto_generated_reason"] = reason
                result["auto_generated_exercises"] = [serialize_exercise(e) for e in added]
        except Exception as e:
            # Generation is a bonus, never a reason to fail the answer.
            logger.warning("Auto-variant generation failed for skill %s: %s",
                           exercise.skill_tag, e)

    return result


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


@router.get("/api/skills/{user_id}/mastery")
async def get_skill_mastery(user_id: int, db: Session = Depends(get_db)):
    """Status of every curriculum skill the learner has attempts for (services/mastery.py)."""
    user = get_user_or_404(db, user_id)
    mastery = skill_mastery(db, user_id, user.target_language)
    from backend.models.topic import Topic

    entry_ids = dict(db.query(Topic.skill_id, Topic.id).filter(
        Topic.user_id == user_id, Topic.skill_id.isnot(None)).all())
    for m in mastery.values():
        m["knowledge_topic_id"] = entry_ids.get(m["skill_id"])  # its Bank wiedzy entry
    return {
        "user_id": user_id,
        "language": user.target_language,
        "thresholds": {"accuracy": MASTERY_ACCURACY, "window": WINDOW,
                       "min_attempts": MIN_ATTEMPTS, "correct_days": MASTERY_DAYS},
        "skills": sorted(mastery.values(), key=lambda m: m["skill_id"]),
    }


def _hub_exercises_query(db: Session, user_id: int, language: str):
    """Exercises the hub's review deck schedules (decision D1, one deck): items made
    from conversation errors and items the learner once got wrong. Membership only
    grows (both conditions are sticky), so the hub never sees an item vanish."""
    return db.query(Exercise).filter(
        Exercise.user_id == user_id,
        Exercise.language == language,
        Exercise.is_active == True,  # noqa: E712
        or_(
            Exercise.exercise_type == "error_correction",
            Exercise.first_attempt_incorrect == True,  # noqa: E712
            Exercise.lapses > 0,
        ),
    )


@router.get("/api/exercises/{user_id}/for-hub")
async def list_exercises_for_hub(user_id: int, limit: int = 500, offset: int = 0,
                                 db: Session = Depends(get_db)):
    """Error items with their answers and FSRS state, for the hub's Powtórki.
    Read-only; behind the app access gate like every /api route."""
    user = get_user_or_404(db, user_id)
    limit = max(1, min(limit, 1000))
    query = _hub_exercises_query(db, user_id, user.target_language)
    total = query.count()
    rows = query.order_by(Exercise.created_at.asc(), Exercise.id.asc()).offset(max(0, offset)).limit(limit).all()

    def iso(dt):
        return dt.isoformat() if dt else None

    def skill_of(ex):
        return ex.skill_id or find_skill_id(ex.skill_tag)

    return {
        "user_id": user_id,
        "total": total,
        "exercises": [{
            "id": ex.id,
            "prompt": ex.prompt,
            "answer": ex.answer,
            "instruction": ex.instruction,
            "feedback": ex.feedback,
            "exercise_type": ex.exercise_type,
            "skill_id": skill_of(ex),
            "skill_name": skill_name(skill_of(ex)) if skill_of(ex) else None,
            "language": ex.language,
            "cefr_level": ex.cefr_level,
            "is_active": ex.is_active,
            "created_at": iso(ex.created_at),
            "repetitions": ex.repetitions or 0,
            "fsrs_state": ex.fsrs_state,
            "fsrs_step": ex.fsrs_step,
            "stability": ex.stability,
            "difficulty": ex.difficulty,
            "lapses": ex.lapses or 0,
            "interval_days": ex.interval_days,
            "next_review_date": iso(ex.next_review_date),
            "last_review_date": iso(ex.last_review_date),
        } for ex in rows],
    }


@router.post("/api/exercises/{exercise_id}/hub-review")
async def hub_review_exercise(
    exercise_id: int,
    request: HubReviewRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    """A review of an error item done in the hub's Powtórki. Same contract as
    /api/flashcards/{id}/hub-review: the hub's new schedule is stored as-is, 409 when
    the item was answered here after the hub's review, idempotent per client_event_id.
    The rating also counts as an attempt of the item's skill (mastery)."""
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    if exercise.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to review this exercise")
    if already_applied(db, request.client_event_id):
        return {"success": True, "duplicate": True, "exercise_id": exercise_id}

    st = request.state
    if st.fsrs_state not in ("Learning", "Review", "Relearning"):
        raise HTTPException(status_code=422, detail="fsrs_state must be Learning, Review or Relearning")
    reviewed_at = parse_occurred_at(request.reviewed_at)
    last = exercise.last_review_date
    if last is not None and (last if last.tzinfo else last.replace(tzinfo=timezone.utc)) > reviewed_at:
        raise HTTPException(status_code=409, detail="Exercise has a newer review in LinguaAI")
    if st.next_review_date is None:
        next_review = parse_occurred_at(None)
    else:
        try:
            next_review = datetime.fromisoformat(st.next_review_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=422, detail="next_review_date must be ISO 8601")
        if next_review.tzinfo is None:
            next_review = next_review.replace(tzinfo=timezone.utc)
        next_review = next_review.astimezone(timezone.utc)  # SQLite drops the offset

    exercise.fsrs_state = st.fsrs_state
    exercise.fsrs_step = None if st.fsrs_state == "Review" else (st.fsrs_step or 0)
    exercise.stability = st.stability
    exercise.difficulty = st.difficulty
    exercise.repetitions = st.repetitions
    exercise.lapses = st.lapses
    exercise.interval_days = max(1, st.interval_days)
    exercise.next_review_date = next_review
    exercise.last_review_date = reviewed_at
    exercise.retrievability = 1.0
    exercise.times_seen = (exercise.times_seen or 0) + 1
    if request.rating >= 3:
        exercise.times_correct = (exercise.times_correct or 0) + 1

    record_attempt(
        db, user_id=user_id, language=exercise.language,
        skill_id=exercise.skill_id or find_skill_id(exercise.skill_tag), source="hub",
        correct=request.rating >= 3, occurred_at=reviewed_at, exercise_id=exercise.id,
    )
    record_event(db, request.client_event_id, user_id, "exercise_hub_review", exercise.id, reviewed_at)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"success": True, "duplicate": True, "exercise_id": exercise_id}
    return {
        "success": True,
        "duplicate": False,
        "exercise_id": exercise_id,
        "state": exercise.fsrs_state,
        "next_review": exercise.next_review_date.isoformat(),
    }
