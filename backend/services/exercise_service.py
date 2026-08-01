"""Exercise bank service — persist, schedule, mix and refresh practice items.

Design notes:
- Every exercise generated inside a lesson is persisted once (``create_exercises_from_lesson``)
  so equivalent practice never has to be paid for twice.
- Practice sets are assembled from three sources (``build_practice_set``):
  1. items due for spaced retrieval (FSRS, same scheduler as flashcards),
  2. items interleaved from *other* topics (Rohrer & Taylor 2007),
  3. fresh variants for skills the learner keeps getting wrong, or for items that
     have been seen so often that the answer may be memorised rather than the
     rule (Schmidt & Bjork 1992 — variability of practice).
"""
import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models.exercise import Exercise
from backend.services.fsrs_service import apply_fsrs

logger = logging.getLogger(__name__)

# An item seen this many times is a candidate for a fresh variant: at this point
# a learner may be recalling the specific answer rather than applying the rule.
VARIANT_AFTER_TIMES_SEEN = 4
# Share of a practice set reserved for interleaved items from other topics.
INTERLEAVE_RATIO = 0.4

# ── Auto-variant on a struggle streak ────────────────────────────────────────
# When a learner keeps failing one skill we top up the bank *without* waiting for
# them to press "generate". To keep the project's contract that AI spend is
# deliberate and never hidden, this is bounded on three sides:
#   1. a real track record is required (not one unlucky slip),
#   2. accuracy must be genuinely poor ("a series of errors", not the odd miss),
#   3. it self-limits — once unseen fresh variants for the skill exist, it stops,
#      so a persistently-weak skill triggers one top-up, not one per wrong answer.
# The answer endpoint also reports what it generated, so the spend stays visible.
AUTO_VARIANT_MIN_ATTEMPTS = 3    # total attempts on the skill before we act
AUTO_VARIANT_MAX_ACCURACY = 0.5  # "series of errors" = missing more than half
AUTO_VARIANT_FRESH_TARGET = 2    # stop once this many unseen variants await


def _fingerprint(prompt: str, answer: str) -> str:
    """Stable identity for dedup — same question+answer is the same item."""
    raw = f"{(prompt or '').strip().lower()}|{(answer or '').strip().lower()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def flatten_lesson_exercises(lesson_content: dict) -> list[dict]:
    """Flatten a lesson's nested exercises structure into individual items.

    Lesson format: ``exercises: [{type, instruction, skill_tag, feedback, items: [{prompt, answer}]}]``
    Returns one dict per practisable item.
    """
    out: list[dict] = []
    blocks = (lesson_content or {}).get("exercises")
    if not isinstance(blocks, list):
        return out
    for block in blocks:
        if not isinstance(block, dict):
            continue
        items = block.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            prompt = (item.get("prompt") or "").strip()
            answer = (item.get("answer") or "").strip()
            if not prompt or not answer:
                continue
            out.append({
                "prompt": prompt,
                "answer": answer,
                "exercise_type": block.get("type"),
                "instruction": block.get("instruction"),
                "feedback": block.get("feedback"),
                "skill_tag": (block.get("skill_tag") or "").strip() or None,
            })
    return out


def create_exercises_from_lesson(
    db: Session,
    lesson_content: dict,
    user_id: int,
    language: str,
    cefr_level: str,
    lesson_id: int | None = None,
    topic: str | None = None,
) -> int:
    """Persist a lesson's exercises into the bank. Returns how many were added."""
    items = flatten_lesson_exercises(lesson_content)
    if not items:
        return 0

    existing = db.query(Exercise.prompt, Exercise.answer).filter(
        Exercise.user_id == user_id,
        Exercise.language == language,
    ).all()
    seen = {_fingerprint(p, a) for p, a in existing}

    added = 0
    for item in items:
        fp = _fingerprint(item["prompt"], item["answer"])
        if fp in seen:
            continue
        seen.add(fp)
        db.add(Exercise(
            user_id=user_id,
            language=language,
            cefr_level=cefr_level,
            exercise_type=item["exercise_type"],
            instruction=item["instruction"],
            prompt=item["prompt"],
            answer=item["answer"],
            feedback=item["feedback"],
            skill_tag=item["skill_tag"],
            topic=topic,
            source_lesson_id=lesson_id,
        ))
        added += 1
    return added


def serialize_exercise(ex: Exercise, include_answer: bool = False) -> dict:
    """Serialize an exercise for the API. The answer is withheld until review."""
    data = {
        "id": ex.id,
        "exercise_type": ex.exercise_type,
        "instruction": ex.instruction,
        "prompt": ex.prompt,
        "skill_tag": ex.skill_tag,
        "topic": ex.topic,
        "times_seen": ex.times_seen,
        "is_due": True,
    }
    if include_answer:
        data["answer"] = ex.answer
        data["feedback"] = ex.feedback
    return data


def build_practice_set(
    db: Session,
    user_id: int,
    language: str,
    size: int = 10,
    current_topic: str | None = None,
) -> dict:
    """Assemble a mixed practice set from the bank.

    Returns due items first, then interleaved items from other topics, and
    reports which skills look weak enough to warrant freshly generated variants.
    """
    now = datetime.now(timezone.utc)
    base = db.query(Exercise).filter(
        Exercise.user_id == user_id,
        Exercise.language == language,
        Exercise.is_active == True,  # noqa: E712
    )

    due = base.filter(Exercise.next_review_date <= now).order_by(
        Exercise.next_review_date.asc()
    ).limit(size).all()

    # Interleave: items from topics other than the one just studied
    interleave_target = max(1, int(size * INTERLEAVE_RATIO))
    chosen_ids = {e.id for e in due}
    interleaved: list[Exercise] = []
    if len(due) < size:
        q = base.filter(~Exercise.id.in_(chosen_ids)) if chosen_ids else base
        if current_topic:
            q = q.filter((Exercise.topic != current_topic) | (Exercise.topic.is_(None)))
        interleaved = q.order_by(Exercise.next_review_date.asc()).limit(
            min(interleave_target, size - len(due))
        ).all()

    selected = (due + interleaved)[:size]
    return {
        "exercises": [serialize_exercise(e) for e in selected],
        "due_count": len(due),
        "interleaved_count": len(interleaved),
        "weak_skills": find_weak_skills(db, user_id, language),
        "needs_variant": [e.id for e in selected if (e.times_seen or 0) >= VARIANT_AFTER_TIMES_SEEN],
    }


def find_weak_skills(db: Session, user_id: int, language: str, limit: int = 5) -> list[str]:
    """Skills where the learner's accuracy in the bank is weakest.

    Only counts skills actually practised (times_seen > 0), so a fresh bank
    reports nothing rather than flagging everything as weak.
    """
    rows = db.query(Exercise).filter(
        Exercise.user_id == user_id,
        Exercise.language == language,
        Exercise.skill_tag.isnot(None),
        Exercise.times_seen > 0,
    ).all()

    agg: dict[str, list[int]] = {}
    for ex in rows:
        seen, correct = agg.setdefault(ex.skill_tag, [0, 0])
        agg[ex.skill_tag] = [seen + (ex.times_seen or 0), correct + (ex.times_correct or 0)]

    scored = [
        (skill, correct / seen)
        for skill, (seen, correct) in agg.items()
        if seen > 0
    ]
    scored.sort(key=lambda x: x[1])
    return [skill for skill, acc in scored if acc < 0.8][:limit]


def _has_fresh_variants(db: Session, user_id: int, language: str, skill_tag: str) -> bool:
    """True if the skill already has unseen fresh variants waiting in the bank.

    The shared cost guard for both auto-variant triggers: if fresh material
    exists, the learner has something new to face, so we do not spend on more.
    """
    fresh = db.query(Exercise).filter(
        Exercise.user_id == user_id,
        Exercise.language == language,
        Exercise.skill_tag == skill_tag,
        Exercise.is_active == True,  # noqa: E712
        Exercise.times_seen == 0,
    ).count()
    return fresh >= AUTO_VARIANT_FRESH_TARGET


def skill_needs_auto_variant(
    db: Session, user_id: int, language: str, skill_tag: str | None
) -> bool:
    """Failure trigger: a skill is being failed enough to warrant fresh variants.

    "A series of errors" is read from the bank's aggregate accuracy for the skill
    (no separate per-answer log): at least ``AUTO_VARIANT_MIN_ATTEMPTS`` attempts
    with accuracy at or below ``AUTO_VARIANT_MAX_ACCURACY``, and no fresh variants
    already waiting (the cost guard).
    """
    if not skill_tag:
        return False

    rows = db.query(Exercise.times_seen, Exercise.times_correct).filter(
        Exercise.user_id == user_id,
        Exercise.language == language,
        Exercise.skill_tag == skill_tag,
        Exercise.is_active == True,  # noqa: E712
    ).all()
    seen = sum((r[0] or 0) for r in rows)
    correct = sum((r[1] or 0) for r in rows)
    if seen < AUTO_VARIANT_MIN_ATTEMPTS:
        return False
    if seen == 0 or (correct / seen) > AUTO_VARIANT_MAX_ACCURACY:
        return False
    return not _has_fresh_variants(db, user_id, language, skill_tag)


def skill_memorized_needs_variant(
    db: Session, user_id: int, language: str, skill_tag: str | None, item_times_seen: int
) -> bool:
    """Memorization trigger: an item has been seen so often that the learner may
    be recalling the specific answer rather than applying the rule (Schmidt &
    Bjork 1992 — variability of practice). Spawn a fresh same-skill variant so
    the skill is re-practised on new surface forms — unless fresh material for
    the skill is already waiting (the shared cost guard).
    """
    if not skill_tag or (item_times_seen or 0) < VARIANT_AFTER_TIMES_SEEN:
        return False
    return not _has_fresh_variants(db, user_id, language, skill_tag)


def grade_answer(expected: str, given: str) -> bool:
    """Lenient exact-match grading: case-, whitespace- and punctuation-insensitive."""
    import re
    norm = lambda s: re.sub(r"[^\w\s]", "", (s or "").strip().lower())  # noqa: E731
    return bool(norm(expected)) and norm(expected) == norm(given)


def review_exercise(
    db: Session,
    exercise: Exercise,
    rating: int,
    now: datetime | None = None,
) -> dict:
    """Apply FSRS to an exercise review and update exposure counters.

    ``now`` lets a replayed offline answer be scheduled from the moment the
    learner actually answered rather than from when the device reconnected.
    """
    now = now or datetime.now(timezone.utc)
    result = apply_fsrs(
        rating=rating,
        difficulty=exercise.difficulty,
        stability=exercise.stability,
        retrievability=exercise.retrievability if exercise.retrievability else None,
        reps=exercise.repetitions or 0,
        lapses=exercise.lapses or 0,
        current_state=exercise.fsrs_state or "Learning",
        last_review_date=exercise.last_review_date,
    )

    exercise.difficulty = result.difficulty
    exercise.stability = result.stability
    exercise.retrievability = result.retrievability
    exercise.interval_days = result.interval
    exercise.repetitions = result.repetitions
    exercise.lapses = result.lapses
    exercise.fsrs_state = result.state
    exercise.next_review_date = result.next_review_date
    exercise.last_review_date = now
    exercise.times_seen = (exercise.times_seen or 0) + 1
    if rating >= 3:
        exercise.times_correct = (exercise.times_correct or 0) + 1

    return {
        "interval_days": result.interval,
        "state": result.state,
        "next_review": result.next_review_date.isoformat(),
        "times_seen": exercise.times_seen,
        "times_correct": exercise.times_correct,
        "needs_variant": exercise.times_seen >= VARIANT_AFTER_TIMES_SEEN,
    }
