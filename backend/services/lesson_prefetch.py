"""Prepare the next lesson ahead of time (A10).

Generating a lesson takes long (the multi-section prompt alone ran over 110 s
on the best tier, and the German check of A7 adds a second call), so the
learner used to wait on the "Lekcja" page. Now the next lesson is generated in
the background right after a lesson is completed, and once at start-up for a
learner whose last lesson is completed. GET /api/lessons/today then finds it as
the uncompleted lesson from a previous day, exactly as a lesson left unfinished.

At most one lesson waits ahead: nothing is generated while an uncompleted
lesson exists, so a day without studying costs no extra lesson.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from backend.config import settings
from backend.database import SessionLocal
from backend.models.lesson import Lesson
from backend.models.study_plan import StudyPlan
from backend.models.user import User
from backend.services.audio_service import generate_full_lesson_audio
from backend.services.lesson_generator import generate_daily_lesson
from backend.services.lesson_service import create_and_persist_lesson, gather_lesson_context
from backend.services.mastery import apply_module_gate
from backend.services.topic_service import process_lesson_topics_bg

logger = logging.getLogger(__name__)

ACTIVE_DAYS = 14  # start-up prefetch only for someone who studied recently
_locks: dict[int, asyncio.Lock] = {}


def _enabled() -> bool:
    return settings.PREPARE_NEXT_LESSON


async def prepare_next_lesson(user_id: int) -> int | None:
    """Generate and save the user's next lesson; return its id, or None when not needed."""
    if not _enabled():
        return None
    lock = _locks.setdefault(user_id, asyncio.Lock())
    if lock.locked():
        return None  # already being prepared
    async with lock:
        db = SessionLocal()
        try:
            return await _prepare(db, user_id)
        except Exception as e:  # the learner then gets the lesson generated on the page, as before
            logger.error(f"Preparing the next lesson for user {user_id} failed: {e}")
            db.rollback()
            return None
        finally:
            db.close()


async def _prepare(db, user_id: int) -> int | None:
    # Imported here: the lessons router imports this service
    from backend.routers.lessons import get_day_number

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    language = user.target_language
    plan = db.query(StudyPlan).filter(StudyPlan.user_id == user_id, StudyPlan.is_active == True).first()  # noqa: E712
    if not plan:
        return None
    pending = db.query(Lesson.id).filter(
        Lesson.user_id == user_id, Lesson.language == language, Lesson.is_completed == False,  # noqa: E712
    ).first()
    if pending:
        return None
    day_number = get_day_number(user, db, language)  # the number GET /today would generate
    if db.query(Lesson.id).filter(Lesson.user_id == user_id, Lesson.language == language,
                                  Lesson.day_number == day_number).first():
        return None

    started = datetime.now()
    content = await generate_daily_lesson(
        user_id=user_id,
        target_language=language,
        native_language=user.native_language,
        cefr_level=user.cefr_level,
        day_number=day_number,
        db=db,
        study_plan_data=apply_module_gate(db, plan, day_number),
        **gather_lesson_context(db, user),
    )
    try:
        lesson = create_and_persist_lesson(db, user, day_number, content)
    except IntegrityError:
        db.rollback()  # the page generated the same day at the same moment
        return None
    seconds = (datetime.now() - started).total_seconds()
    logger.info(f"Next lesson prepared: user {user_id}, day {day_number}, {seconds:.0f} s")

    await generate_full_lesson_audio(content, language, lesson.id)
    await process_lesson_topics_bg(
        user_id=lesson.user_id, language=lesson.language, cefr_level=lesson.cefr_level,
        lesson_id=lesson.id, day_number=lesson.day_number, lesson_title=lesson.title, content=content,
    )
    return lesson.id


def active_learners(db) -> list[int]:
    """Users with an active plan who completed a lesson in the last ACTIVE_DAYS days."""
    since = datetime.utcnow() - timedelta(days=ACTIVE_DAYS)
    rows = db.query(Lesson.user_id).join(
        StudyPlan, (StudyPlan.user_id == Lesson.user_id) & (StudyPlan.is_active == True),  # noqa: E712
    ).filter(Lesson.is_completed == True, Lesson.completed_at >= since).distinct().all()  # noqa: E712
    return [r[0] for r in rows]


async def prepare_for_active_learners() -> None:
    """Start-up: prepare lessons for learners whose last lesson is completed."""
    if not _enabled():
        return
    db = SessionLocal()
    try:
        users = active_learners(db)
    finally:
        db.close()
    for user_id in users:
        await prepare_next_lesson(user_id)
