"""Business logic for the lessons router, extracted per ACTION_PLAN.md F2-1:
`backend/routers/lessons.py` had grown business logic beyond
request-parsing/response-mapping (the Router -> Service -> Session pattern
CLAUDE.md documents everywhere else). Two pieces were duplicated verbatim
between `get_today_lesson` and `generate_next_lesson` — a real DRY/bug-risk
problem, not just a style nit — and are the ones extracted here:

- gather_lesson_context(): the RAG context-gathering (recent test errors,
  interleaving topics, known vocabulary, weak/strong topics) that feeds
  generate_daily_lesson().
- create_and_persist_lesson(): saving the generated lesson, then creating
  its flashcards and exercises.

The IntegrityError race-recovery (the actual bug fixed in commit 4af0665)
stays in the router: only `get_today_lesson` can race (the frontend's
double-mount fires two concurrent requests), and reacting to the exception
by querying for and returning the winner's lesson is a response-shaping
decision, not business logic.
"""
import json
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.test_result import TestResult
from backend.models.topic import Topic
from backend.models.user import User
from backend.services.exercise_service import create_exercises_from_lesson
from backend.services.flashcard_service import create_flashcards_from_vocab


def lesson_to_dict(lesson: Lesson) -> dict:
    """Serialize a Lesson row to the shape every lesson-read endpoint returns."""
    return {
        "lesson_id": lesson.id,
        "day_number": lesson.day_number,
        "title": lesson.title,
        "topic": lesson.topic,
        "content": json.loads(lesson.content),
        "is_completed": lesson.is_completed,
        "language": lesson.language,
        "cefr_level": lesson.cefr_level,
        "created_at": lesson.created_at.isoformat(),
    }


def get_recent_errors(user_id: int, db: Session, limit: int = 10) -> list:
    """Recent TEST errors give the lesson a coarse sense of assessed weaknesses.
    Fine-grained remediation of individual exercise mistakes is NOT done here —
    it lives in the exercise bank (a failed/over-familiar skill spawns fresh
    variants), so the lesson stays about introducing material, not drilling
    specific past slips."""
    recent_tests = db.query(TestResult).filter(
        TestResult.user_id == user_id
    ).order_by(TestResult.created_at.desc()).limit(5).all()

    errors = []
    for test in recent_tests:
        if test.errors:
            try:
                test_errors = json.loads(test.errors)
                errors.extend(test_errors[:3])
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

    return errors[:limit]


def gather_lesson_context(db: Session, user: User) -> dict:
    """RAG context for generate_daily_lesson(): recent test errors, topics
    seen in the last 7 days (for interleaving), known vocabulary (mastered
    words first — SCI-1: the most reliable "known" input for i+1), and
    weak/strong topics by memory_strength. Was duplicated verbatim in
    get_today_lesson and generate_next_lesson before this extraction."""
    user_errors = get_recent_errors(user.id, db)

    week_ago = datetime.combine(date.today() - timedelta(days=7), datetime.min.time())
    recent_lessons = db.query(Lesson).filter(
        Lesson.user_id == user.id,
        Lesson.created_at >= week_ago
    ).order_by(Lesson.created_at.desc()).limit(7).all()
    recent_topics = [l.topic for l in recent_lessons if l.topic] if recent_lessons else None

    user_flashcards = db.query(Flashcard.word).filter(
        Flashcard.user_id == user.id,
        Flashcard.language == user.target_language,
        Flashcard.is_active == True,
    ).order_by(Flashcard.is_mastered.desc(), Flashcard.created_at.desc()).limit(50).all()
    user_vocabulary = [f[0] for f in user_flashcards] if user_flashcards else None

    all_topics = db.query(Topic).filter(
        Topic.user_id == user.id,
        Topic.language == user.target_language,
    ).order_by(Topic.memory_strength.asc()).all()
    weak_topics = [t.name for t in all_topics if t.memory_strength < 0.5][:5] if all_topics else None
    strong_topics = [t.name for t in reversed(all_topics) if t.memory_strength >= 0.7][:3] if all_topics else None

    return {
        "user_errors": user_errors,
        "recent_topics": recent_topics,
        "user_vocabulary": user_vocabulary,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
    }


def create_and_persist_lesson(db: Session, user: User, day_number: int, lesson_content: dict) -> Lesson:
    """Save the generated lesson, then create its flashcards and exercise-bank
    entries. Does NOT handle the concurrent-request IntegrityError race — the
    caller (get_today_lesson) is the only endpoint that can race and decides
    how to recover; letting it propagate here keeps that decision in the
    router where the response-shaping for the recovery path also lives."""
    lesson = Lesson(
        user_id=user.id,
        day_number=day_number,
        title=lesson_content.get("title", f"Dzień {day_number}"),
        topic=lesson_content.get("topic", "General"),
        content=json.dumps(lesson_content),
        cefr_level=user.cefr_level,
        language=user.target_language,
        is_completed=False,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    create_flashcards_from_vocab(
        db, lesson_content.get("vocabulary", []),
        user.id, user.target_language, user.cefr_level,
        lesson.id, lesson.day_number, lesson.topic,
    )
    create_exercises_from_lesson(
        db, lesson_content, user.id, user.target_language,
        user.cefr_level, lesson.id, lesson.topic,
    )
    db.commit()
    return lesson
