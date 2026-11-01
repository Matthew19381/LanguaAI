"""Per-skill mastery from review answers and conversation errors (21.10.2026).

Ties the curriculum (services/curriculum.py) to what the learner actually gets
right and wrong:

- every answer to an exercise with a skill id, and every conversation error the
  analysis tags with one, is logged as a ``SkillAttempt``;
- ``skill_mastery`` turns the log into a status per skill;
- ``review_context`` gives the next lesson a warm-up on recent errors and weak skills;
- ``apply_module_gate`` inserts a repair day before a new module when a grammar
  point of the previous module is weak (mastery learning: corrective work and a
  re-check before moving on, Bloom; Kulik, Kulik & Bangert-Drowns 1990);
- ``cards_from_conversation_errors`` turns a conversation error into a review item.

Thresholds are assumptions to tune, not results of one study: 80% is the usual
mastery criterion in mastery-learning programmes; "correct on 3 different days"
follows successive relearning (Rawson, Dunlosky & Sciartelli 2013: 3 correct
recalls, then spaced relearning sessions).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.models.exercise import Exercise
from backend.models.skill_attempt import SkillAttempt
from backend.services.curriculum import MODULES, SKILLS, find_skill_id, module_index, skill_name
from backend.services.local_day import local_date, on_local_day

MASTERY_ACCURACY = 0.8      # share of correct first tries among the last WINDOW
WINDOW = 10                 # recent first tries that count
MIN_ATTEMPTS = 5            # fewer first tries = not enough data, never weak or mastered
MASTERY_DAYS = 3            # correct answers on at least this many different days
ERROR_LOOKBACK_DAYS = 14    # errors this recent go into the lesson warm-up
MAX_REPAIR_DAYS = 2         # repair days per module boundary, so the plan cannot stall
MAX_CARDS_PER_CONVERSATION = 5


def _utc(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def record_attempt(
    db: Session,
    *,
    user_id: int,
    language: str,
    skill_id: str | None,
    source: str,
    correct: bool,
    occurred_at: datetime | None = None,
    exercise_id: int | None = None,
    detail: dict | None = None,
) -> SkillAttempt | None:
    """Log one attempt. Ignored without a catalog skill id. A second answer to the
    same exercise on the same day is kept but marked ``first_try = False``."""
    if skill_id not in SKILLS:
        return None
    occurred_at = _utc(occurred_at) or datetime.now(timezone.utc)
    first_try = True
    if exercise_id is not None:
        earlier = db.query(SkillAttempt.id).filter(
            SkillAttempt.exercise_id == exercise_id,
            on_local_day(SkillAttempt.occurred_at, local_date(occurred_at)),  # the learner's day
        ).first()
        first_try = earlier is None
    attempt = SkillAttempt(
        user_id=user_id,
        language=language,
        skill_id=skill_id,
        source=source,
        correct=bool(correct),
        first_try=first_try,
        exercise_id=exercise_id,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        occurred_at=occurred_at.replace(tzinfo=None),
    )
    db.add(attempt)
    return attempt


def skill_mastery(db: Session, user_id: int, language: str) -> dict[str, dict]:
    """Status per skill that has attempts: ``za_malo_danych``, ``slaba``,
    ``w_nauce`` (accurate, but not yet on enough different days) or ``opanowana``."""
    rows = db.query(SkillAttempt).filter(
        SkillAttempt.user_id == user_id,
        SkillAttempt.language == language,
        SkillAttempt.first_try == True,  # noqa: E712
    ).order_by(SkillAttempt.occurred_at.asc(), SkillAttempt.id.asc()).all()

    by_skill: dict[str, list[SkillAttempt]] = {}
    for row in rows:
        by_skill.setdefault(row.skill_id, []).append(row)

    out = {}
    for skill_id, attempts in by_skill.items():
        recent = attempts[-WINDOW:]
        accuracy = sum(1 for a in recent if a.correct) / len(recent)
        correct_days = len({local_date(a.occurred_at) for a in attempts if a.correct})
        errors = [a.occurred_at for a in attempts if not a.correct]
        if len(attempts) < MIN_ATTEMPTS:
            status = "za_malo_danych"
        elif accuracy < MASTERY_ACCURACY:
            status = "slaba"
        elif correct_days >= MASTERY_DAYS:
            status = "opanowana"
        else:
            status = "w_nauce"
        out[skill_id] = {
            "skill_id": skill_id,
            "name": skill_name(skill_id) if skill_id in SKILLS else skill_id,
            "status": status,
            "attempts": len(attempts),
            "accuracy": round(accuracy, 2),
            "correct_days": correct_days,
            "last_error": _utc(max(errors)).isoformat() if errors else None,
        }
    return out


def review_context(db: Session, user_id: int, language: str, now: datetime | None = None) -> dict | None:
    """What the next lesson's warm-up should go back to: weak skills (worst first)
    and the learner's own recent errors with the right form. None when there is nothing."""
    now = _utc(now) or datetime.now(timezone.utc)
    mastery = skill_mastery(db, user_id, language)
    weak = sorted((m for m in mastery.values() if m["status"] == "slaba"), key=lambda m: m["accuracy"])

    since = (now - timedelta(days=ERROR_LOOKBACK_DAYS)).replace(tzinfo=None)
    rows = db.query(SkillAttempt).filter(
        SkillAttempt.user_id == user_id,
        SkillAttempt.language == language,
        SkillAttempt.correct == False,  # noqa: E712
        SkillAttempt.occurred_at >= since,
        SkillAttempt.detail.isnot(None),
    ).order_by(SkillAttempt.occurred_at.desc()).limit(20).all()
    errors, seen = [], set()
    for row in rows:
        try:
            detail = json.loads(row.detail)
        except (TypeError, ValueError):
            continue
        key = (detail.get("wrong") or "", detail.get("correct") or "")
        if key in seen or not key[1]:
            continue
        seen.add(key)
        errors.append({"skill_id": row.skill_id, **detail})
        if len(errors) == 5:
            break

    if not weak and not errors:
        return None
    return {
        "weak_skills": [{"skill_id": m["skill_id"], "name": m["name"], "accuracy": m["accuracy"]}
                        for m in weak[:3]],
        "errors": errors,
    }


def apply_module_gate(db: Session, study_plan, day_number: int) -> dict:
    """Return the plan for ``day_number``. On the first day of a new module, when a
    grammar point of the previous module is weak, a repair day is inserted at
    ``day_number`` (later days move by one) and the plan is saved. At most
    MAX_REPAIR_DAYS per module boundary; skills without enough data never block."""
    plan = json.loads(study_plan.plan_data)
    if not plan.get("curriculum_id") or not isinstance(plan.get("daily_topics"), list):
        return plan
    days = plan["daily_topics"]
    entry = next((d for d in days if isinstance(d, dict) and d.get("day") == day_number), None)
    if not entry or entry.get("day_in_module") != 1:
        return plan
    index = module_index(entry.get("module_id"))
    if not index:
        return plan
    prev = MODULES[index - 1]
    repairs = sum(1 for d in days if isinstance(d, dict) and d.get("repair_of") == prev["id"])
    if repairs >= MAX_REPAIR_DAYS:
        return plan

    mastery = skill_mastery(db, study_plan.user_id, study_plan.language)
    weak = [g for g in dict.fromkeys(prev["grammar"]) if mastery.get(g, {}).get("status") == "slaba"]
    if not weak:
        return plan

    for d in days:
        if isinstance(d, dict) and isinstance(d.get("day"), int) and d["day"] >= day_number:
            d["day"] += 1
    repair = {
        "day": day_number,
        "module_id": prev["id"],
        "phase": prev["phase"],
        "day_in_module": 15 + repairs,
        "day_type": "naprawa",
        "day_type_pl": "powtórka naprawcza",
        "grammar_topic": "; ".join(skill_name(g) for g in weak),
        "vocabulary_theme": f"{prev['theme']}: powtórka",
        "conversation_topic": prev["task"],
        "skill_ids": weak + [prev["speaking"]],
        "module_task": prev["task"],
        "repair_of": prev["id"],
    }
    days.insert(days.index(entry), repair)
    study_plan.plan_data = json.dumps(plan, ensure_ascii=False)
    study_plan.updated_at = datetime.now(timezone.utc)
    db.commit()
    return plan


def cards_from_conversation_errors(
    db: Session,
    *,
    user_id: int,
    language: str,
    cefr_level: str | None,
    errors: list,
    occurred_at: datetime | None = None,
) -> int:
    """Each conversation error with the learner's phrase and the right form becomes
    an error-correction item in the exercise bank (due at once, then FSRS), and,
    when it names a catalog skill, a failed attempt for that skill. Returns the
    number of new items."""
    from backend.services.exercise_service import _fingerprint

    existing = db.query(Exercise.prompt, Exercise.answer).filter(
        Exercise.user_id == user_id, Exercise.language == language,
    ).all()
    seen = {_fingerprint(p, a) for p, a in existing}
    added = 0
    for err in (errors or [])[:MAX_CARDS_PER_CONVERSATION]:
        if not isinstance(err, dict):
            continue
        wrong = str(err.get("question") or "").strip()
        right = str(err.get("correct_answer") or "").strip()
        if not wrong or not right or wrong == right:
            continue
        skill_id = find_skill_id(err.get("skill_id"))
        record_attempt(
            db, user_id=user_id, language=language, skill_id=skill_id, source="conversation",
            correct=False, occurred_at=occurred_at,
            detail={"wrong": wrong, "correct": right},
        )
        fp = _fingerprint(wrong, right)
        if fp in seen:
            continue
        seen.add(fp)
        db.add(Exercise(
            user_id=user_id,
            language=language,
            cefr_level=cefr_level,
            exercise_type="error_correction",
            instruction="Popraw zdanie z rozmowy",
            prompt=wrong,
            answer=right,
            feedback=str(err.get("explanation") or "") or None,
            skill_tag=skill_id or (str(err.get("type") or "") or None),
            skill_id=skill_id,
            topic="Błędy z rozmów",
        ))
        added += 1
    return added
