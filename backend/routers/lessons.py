import json
import logging
import os
from datetime import date, datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.study_plan import StudyPlan
from backend.models.test_result import TestResult
from backend.models.user import User
from backend.schemas.lesson import (
    CompleteLessonRequest,
    EvaluateProductionRequest,
)
from backend.services import hub_events, lesson_prefetch
from backend.services.audio_service import (
    generate_full_lesson_audio,
    generate_lesson_package_audio,
    generate_vocabulary_audio,
)
from backend.services.gemini_service import generate_json as ai_generate_json
from backend.services.gemini_service import with_model
from backend.services.lesson_generator import (
    LessonGenerationError,
    generate_daily_lesson,
    generate_iplus1_content,
)
from backend.services.lesson_generator.tests import lesson_grammar_text
from backend.services.lesson_service import (
    create_and_persist_lesson,
    gather_lesson_context,
    lesson_payload,
)
from backend.services.mastery import apply_module_gate
from backend.services.plan_day import current_lesson, lesson_for_review, next_day_number, todays_lesson
from backend.services.obsidian_service import save_obsidian_md
from backend.services.pdf_service import EXPORTS_DIR, generate_lesson_pdf
from backend.services.streak_service import calculate_streak
from backend.services.sync_service import already_applied, parse_occurred_at, record_event
from backend.services.topic_service import process_lesson_topics_bg
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)

router = APIRouter()

LESSON_UNAVAILABLE = ("Nie udało się wygenerować lekcji: model AI nie odpowiada "
                      "(klucz, środki na koncie albo awaria). Nic nie zapisano, spróbuj za chwilę.")


def get_day_number(user: User, db: Session = None, language: str = None) -> int:
    """Day number of the next lesson to generate for a language (plan_day.next_day_number)."""
    if db is not None and language is not None:
        return next_day_number(db, user, language)
    # Fallback: global calendar-based calculation
    if not user.created_at:
        return 1
    delta = date.today() - user.created_at.date()
    return max(1, delta.days + 1)


@router.get("/api/lessons/today/{user_id}")
async def get_today_lesson(user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)

    # The lesson finished today, else the waiting one (plan_day.todays_lesson)
    existing_lesson = todays_lesson(db, user)
    if existing_lesson is None and await lesson_prefetch.wait_if_preparing(user_id):
        # The next lesson was being prepared in the background: use it instead of
        # paying for a second generation of the same day
        db.expire_all()
        existing_lesson = todays_lesson(db, user)

    if existing_lesson:
        return lesson_payload(db, existing_lesson)

    day_number = get_day_number(user, db, user.target_language)

    # Get active study plan
    study_plan = db.query(StudyPlan).filter(
        StudyPlan.user_id == user_id,
        StudyPlan.is_active == True
    ).first()

    if not study_plan:
        raise HTTPException(status_code=404, detail="No active study plan. Please complete placement test first.")

    # Mastery gate: a weak skill of the last module inserts a repair day here
    study_plan_data = apply_module_gate(db, study_plan, day_number)
    context = gather_lesson_context(db, user)

    # Generate new lesson
    try:
        lesson_content = await generate_daily_lesson(
            user_id=user_id,
            target_language=user.target_language,
            native_language=user.native_language,
            cefr_level=user.cefr_level,
            day_number=day_number,
            db=db,
            study_plan_data=study_plan_data,
            **context,
        )
    except LessonGenerationError:
        raise HTTPException(status_code=503, detail=LESSON_UNAVAILABLE)

    # Save lesson + flashcards + exercises (handle race condition via unique constraint)
    try:
        lesson = create_and_persist_lesson(db, user, day_number, lesson_content)
    except IntegrityError:
        # Another concurrent request already created this lesson — rollback and use existing.
        # Recover by the EXACT unique-constraint key (user_id, language, day_number), not by
        # creation date: querying by "created today" can miss the row the other request just
        # committed (observed live — two concurrent requests both generating day N, one wins
        # the insert, the other's recovery query found nothing and re-raised the original
        # IntegrityError as a 500 instead of returning the winner's lesson).
        db.rollback()
        existing_lesson = db.query(Lesson).filter(
            Lesson.user_id == user_id,
            Lesson.language == user.target_language,
            Lesson.day_number == day_number,
        ).first()
        if existing_lesson:
            return lesson_payload(db, existing_lesson)
        raise

    # Generate audio for lesson sections (background, non-blocking)
    background_tasks.add_task(
        generate_full_lesson_audio, lesson_content, user.target_language, lesson.id
    )

    # Extract topics and assign lesson to them (background, non-blocking)
    background_tasks.add_task(
        process_lesson_topics_bg,
        user_id=lesson.user_id,
        language=lesson.language,
        cefr_level=lesson.cefr_level,
        lesson_id=lesson.id,
        day_number=lesson.day_number,
        lesson_title=lesson.title,
        content=lesson_content,
    )

    return lesson_payload(db, lesson)


@router.get("/api/lessons/iplus1/{user_id}")
async def get_iplus1_reading(
    user_id: int,
    topic: str = "daily life",
    db: Session = Depends(get_db),
):
    """SCI-3: generate a comprehensible-input (i+1) reading text and report its
    measured lexical coverage. Uses the learner's mastered words first (SCI-1)
    as the 'known' vocabulary; the generator regenerates if coverage < 95%.
    """
    user = get_user_or_404(db, user_id)

    # Known vocabulary — mastered words first (most reliable "known" input)
    rows = db.query(Flashcard.word).filter(
        Flashcard.user_id == user_id,
        Flashcard.language == user.target_language,
        Flashcard.is_active == True,
    ).order_by(Flashcard.is_mastered.desc(), Flashcard.created_at.desc()).limit(50).all()
    known_words = [r[0] for r in rows]

    result = await generate_iplus1_content(
        known_words=known_words,
        target_language=user.target_language,
        native_language=user.native_language,
        cefr_level=user.cefr_level,
        topic=topic,
    )
    return result


@router.get("/api/lessons/{lesson_id}")
async def get_lesson(lesson_id: int, user_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify ownership
    if lesson.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this lesson")

    return lesson_payload(db, lesson)


@router.post("/api/lessons/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: int,
    request: CompleteLessonRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify ownership
    if request.user_id and lesson.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to complete this lesson")

    # ── Offline replay: a queued completion must never be applied twice ──
    # (double XP / a corrupted streak). Same idempotency ledger as exercise
    # answers and flashcard reviews.
    if already_applied(db, request.client_event_id):
        return {
            "success": True,
            "duplicate": True,
            "lesson_id": lesson.id,
            "is_completed": lesson.is_completed,
            "completed_at": lesson.completed_at.isoformat() if lesson.completed_at else None,
            "xp_awarded": 0,
            "new_achievements": [],
        }

    newly_awarded = []
    xp_awarded = 0
    if not lesson.is_completed:
        # Completed offline yesterday, synced today → the streak must count the
        # day it was actually finished, not the reconnect day. calculate_streak
        # reads completed_at, so pinning it here is enough.
        occurred = parse_occurred_at(request.completed_at)
        lesson.is_completed = True
        lesson.completed_at = occurred

        # Award XP for completing lesson (to the lesson's owner: a replayed offline
        # completion without user_id used to give no XP and no streak)
        user = db.query(User).filter(User.id == lesson.user_id).first()
        if user:
            user.total_xp += 25  # 25 XP for completing a lesson
            xp_awarded = 25
            # Update streak — consecutive days with at least one completed lesson (with freeze support).
            # The session does not autoflush, so without the flush the streak ignored this lesson.
            # streak_freezes is the allowance, not a counter: calculate_streak spends it on the
            # gaps every time, so storing what is left charged the same gaps again next time.
            db.flush()
            streak, _freezes_left = calculate_streak(db, user.id, user.streak_freezes or 0)
            user.streak_days = streak

        record_event(db, request.client_event_id,
                     request.user_id or lesson.user_id,
                     "lesson_complete", lesson.id, occurred)
        # Ticks "LinguaAI: lekcja dnia" in the hub's day plan (sent after the response)
        hub_events.enqueue(db, hub_events.lesson_completed_event(lesson))

        try:
            db.commit()
        except IntegrityError:
            # Two replays raced on the same client_event_id — the other one won.
            db.rollback()
            db.refresh(lesson)
            return {
                "success": True,
                "duplicate": True,
                "lesson_id": lesson.id,
                "is_completed": lesson.is_completed,
                "completed_at": lesson.completed_at.isoformat() if lesson.completed_at else None,
                "xp_awarded": 0,
                "new_achievements": [],
            }

        background_tasks.add_task(hub_events.flush_in_new_session)
        # A10: the next lesson is ready when the learner comes back
        background_tasks.add_task(lesson_prefetch.prepare_next_lesson, lesson.user_id)

        # Check achievements after commit
        from backend.services.achievement_service import check_and_award_achievements
        user = db.query(User).filter(User.id == lesson.user_id).first()
        if user:
            newly_awarded = check_and_award_achievements(user, db)

    return {
        "success": True,
        "lesson_id": lesson.id,
        "is_completed": lesson.is_completed,
        "completed_at": lesson.completed_at.isoformat() if lesson.completed_at else None,
        "xp_awarded": xp_awarded,
        "new_achievements": newly_awarded,
    }


@router.get("/api/lessons/audio/{lesson_id}")
async def get_lesson_audio(lesson_id: int, user_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify ownership
    if lesson.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this lesson")

    content = json.loads(lesson.content)
    vocabulary = content.get("vocabulary", [])

    try:
        audio_files = await generate_vocabulary_audio(
            vocabulary=vocabulary,
            language=lesson.language,
            lesson_id=lesson_id
        )
        return {
            "lesson_id": lesson_id,
            "audio_files": audio_files
        }
    except httpx.RequestError as e:
        logger.error(f"Audio service connection error: {e}")
        raise HTTPException(status_code=503, detail="Audio service unavailable")
    except Exception:
        logger.exception("Unexpected error generating audio")
        raise HTTPException(status_code=500, detail="Failed to generate audio")


@router.get("/api/lessons/{lesson_id}/export-pdf")
async def export_lesson_pdf(lesson_id: int, user_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify ownership
    if lesson.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this lesson")

    content = json.loads(lesson.content)
    lesson_data = {
        "title": lesson.title,
        "topic": lesson.topic,
        "content": content,
    }

    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in lesson.title)[:50]
    filename = f"lesson_{lesson_id}_{safe_title}.pdf"
    output_path = os.path.join(EXPORTS_DIR, filename)

    try:
        generate_lesson_pdf(lesson_data, output_path)
        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=filename,
        )
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/api/lessons/{lesson_id}/export-obsidian")
async def export_lesson_obsidian(
    lesson_id: int,
    user_id: int,
    day_offset: int = Query(0, description="-1=yesterday, 0=today, 1=tomorrow, 2=day after"),
    upload: bool = Query(False, description="Upload to Google Drive instead of downloading"),
    db: Session = Depends(get_db)
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify ownership
    if lesson.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this lesson")

    content = json.loads(lesson.content)
    lesson_data = {
        "title": lesson.title,
        "topic": lesson.topic,
        "content": content,
        "cefr_level": lesson.cefr_level,
        "language": lesson.language,
        "day_number": lesson.day_number,
    }

    # If day_offset > 0, pre-generate a future lesson
    if day_offset > 0:
        user = db.query(User).filter(User.id == lesson.user_id).first()
        if user:
            study_plan = db.query(StudyPlan).filter(
                StudyPlan.user_id == user.id,
                StudyPlan.is_active == True
            ).first()
            if study_plan:
                future_day = lesson.day_number + day_offset
                plan_data = json.loads(study_plan.plan_data)
                try:
                    future_content = await generate_daily_lesson(
                        user_id=lesson.user_id,
                        day_number=future_day,
                        study_plan_data=plan_data,
                        user_errors=[],
                        cefr_level=user.cefr_level,
                        target_language=user.target_language,
                        native_language=user.native_language,
                        recent_topics=[lesson.topic],
                        db=db,
                    )
                    lesson_data = {
                        "title": future_content.get("title", f"Dzień {future_day}"),
                        "topic": future_content.get("topic", ""),
                        "content": future_content,
                        "cefr_level": user.cefr_level,
                        "language": user.target_language,
                        "day_number": future_day,
                    }
                except Exception as e:
                    logger.error(f"Could not pre-generate future lesson: {e}")

    filepath = save_obsidian_md(lesson_data, lesson_id)

    if upload:
        try:
            from backend.services.google_drive_service import upload_to_google_drive
            from backend.services.obsidian_service import _folder_name
            folder_id = os.environ.get("GDRIVE_FOLDER_ID")
            subfolder = _folder_name(lesson_data.get("language", ""), lesson_data.get("cefr_level", "A1"))
            url = upload_to_google_drive(filepath, folder_id, subfolder_name=subfolder)
            return {"success": True, "url": url, "filename": os.path.basename(filepath)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Google Drive upload failed: {e}")

    return FileResponse(
        filepath,
        media_type="text/markdown",
        filename=os.path.basename(filepath),
    )


@router.get("/api/lessons/{lesson_id}/audio-package")
async def download_lesson_audio_package(lesson_id: int, user_id: int, db: Session = Depends(get_db)):
    """Generate and download a ZIP archive with 3 audio files: Gramatyka, Słownictwo, Dialog.
    Also includes a YouTube search URL for a matched video.
    """
    import io
    import urllib.parse
    import zipfile

    from fastapi.responses import StreamingResponse

    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify ownership
    if lesson.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this lesson")

    content = json.loads(lesson.content)
    owner = db.query(User).filter(User.id == lesson.user_id).first()
    audio_files = await generate_lesson_package_audio(
        content, lesson.language, lesson_id, native_language=(owner.native_language if owner else None) or "Polish")

    if not audio_files:
        raise HTTPException(status_code=500, detail="Could not generate audio files")

    # Build ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        name_map = {
            "grammar": "01_Gramatyka.mp3",
            "vocabulary": "02_Słownictwo.mp3",
            "dialogue": "03_Dialog.mp3",
        }
        for key, arcname in name_map.items():
            filepath = audio_files.get(key)
            if filepath and os.path.exists(filepath):
                zf.write(filepath, arcname)

        # Include a text file with YouTube search link
        topic = lesson.topic or lesson.title or "language learning"
        yt_query = urllib.parse.quote(f"{lesson.language} {topic} {lesson.cefr_level}")
        yt_url = f"https://www.youtube.com/results?search_query={yt_query}"
        zf.writestr("video_link.txt", f"Wyszukaj film na YouTube:\n{yt_url}\n")

    zip_buffer.seek(0)
    # ASCII-safe filename (HTTP headers must be latin-1; Polish chars like ł/ń break it)
    _pl_map = str.maketrans({"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z",
                              "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ż": "Z", "Ź": "Z"})
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in (lesson.title or "lesson"))[:30]
    raw_zip_name = f"Lekcja_{lesson.day_number:02d}_{safe_title}.zip"
    zip_name = raw_zip_name.translate(_pl_map)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=\"{zip_name}\""},
    )


@router.get("/api/lessons/list/{user_id}")
async def list_lessons(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)

    lessons = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language
    ).order_by(Lesson.day_number.asc()).all()

    return {
        "lessons": [
            {
                "lesson_id": l.id,
                "day_number": l.day_number,
                "title": l.title,
                "topic": l.topic,
                "is_completed": l.is_completed,
                "cefr_level": l.cefr_level,
                "created_at": l.created_at.isoformat()
            }
            for l in lessons
        ],
        "total": len(lessons),
        "completed": sum(1 for l in lessons if l.is_completed)
    }


@router.get("/api/lessons/history/{user_id}")
async def get_lesson_history(user_id: int, db: Session = Depends(get_db)):
    """Return all lessons for a user ordered by day_number desc, with best test score per day."""
    user = get_user_or_404(db, user_id)

    lessons = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language
    ).order_by(Lesson.created_at.desc()).all()

    # Deduplicate: keep only the first (latest) lesson per day_number
    seen_days: set = set()
    deduped = []
    for l in lessons:
        if l.day_number not in seen_days:
            seen_days.add(l.day_number)
            deduped.append(l)
    lessons = sorted(deduped, key=lambda l: l.day_number, reverse=True)

    # N+1 fix: fetch all test results for this user once, build date→best_score lookup
    all_tests = db.query(TestResult).filter(
        TestResult.user_id == user_id
    ).all()
    tests_by_date: dict = {}
    for t in all_tests:
        d = t.created_at.date() if t.created_at else None
        if d:
            tests_by_date[d] = max(tests_by_date.get(d, 0.0), t.score)

    result = []
    for lesson in lessons:
        lesson_date = lesson.created_at.date() if lesson.created_at else None
        best_score = tests_by_date.get(lesson_date) if lesson_date else None

        result.append({
            "lesson_id": lesson.id,
            "day_number": lesson.day_number,
            "title": lesson.title,
            "topic": lesson.topic,
            "is_completed": lesson.is_completed,
            "created_at": lesson.created_at.isoformat() if lesson.created_at else None,
            "best_test_score": round(best_score, 1) if best_score is not None else None,
        })

    return {"lessons": result, "total": len(result)}


@router.post("/api/lessons/next/{user_id}")
async def generate_next_lesson(user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """The next lesson: the waiting unfinished one, else a new one (max day_number + 1)."""
    user = get_user_or_404(db, user_id)

    # Get active study plan
    study_plan = db.query(StudyPlan).filter(
        StudyPlan.user_id == user_id,
        StudyPlan.is_active == True
    ).first()
    if not study_plan:
        raise HTTPException(status_code=404, detail="No active study plan. Please complete placement test first.")

    # An unfinished lesson waits (usually the one prepared in the background after the
    # last lesson): that is the next lesson. Until 01.11.2026 this generated one more
    # day past it, so the prepared day was skipped and stayed unfinished forever.
    waiting = current_lesson(db, user)
    if waiting is None and await lesson_prefetch.wait_if_preparing(user_id):
        db.expire_all()
        waiting = current_lesson(db, user)
    if waiting is not None:
        return lesson_payload(db, waiting)

    next_day = next_day_number(db, user)

    study_plan_data = apply_module_gate(db, study_plan, next_day)
    context = gather_lesson_context(db, user)

    # Generate lesson
    try:
        lesson_content = await generate_daily_lesson(
            user_id=user_id,
            day_number=next_day,
            study_plan_data=study_plan_data,
            cefr_level=user.cefr_level,
            target_language=user.target_language,
            native_language=user.native_language,
            db=db,
            **context,
        )
    except LessonGenerationError:
        raise HTTPException(status_code=503, detail=LESSON_UNAVAILABLE)

    try:
        lesson = create_and_persist_lesson(db, user, next_day, lesson_content)
    except IntegrityError:
        # Prepared in the background at the same moment: return that lesson
        db.rollback()
        existing = db.query(Lesson).filter(
            Lesson.user_id == user_id, Lesson.language == user.target_language, Lesson.day_number == next_day,
        ).first()
        if existing:
            return lesson_payload(db, existing)
        raise

    background_tasks.add_task(generate_full_lesson_audio, lesson_content, user.target_language, lesson.id)

    # Extract topics (background, non-blocking)
    background_tasks.add_task(
        process_lesson_topics_bg,
        user_id=lesson.user_id,
        language=lesson.language,
        cefr_level=lesson.cefr_level,
        lesson_id=lesson.id,
        day_number=lesson.day_number,
        lesson_title=lesson.title,
        content=lesson_content,
    )

    return lesson_payload(db, lesson)


@router.delete("/api/lessons/reset-today/{user_id}")
async def reset_today_lesson(user_id: int, db: Session = Depends(get_db)):
    """Delete the current unfinished lesson so it gets generated again on the next visit.

    Until 01.11.2026 this deleted every lesson *created* today (UTC): also a lesson
    finished today and the prepared next one, together with all their flashcards and
    the review history; with foreign keys on, a lesson with exercises failed with 500.
    Now only the unfinished lesson goes. Its never-reviewed flashcards and never-answered
    exercises go with it; reviewed ones stay and only lose the link to the lesson.
    """
    from backend.models.exercise import Exercise
    from backend.models.skill_attempt import SkillAttempt
    from backend.models.topic import TopicItem
    user = get_user_or_404(db, user_id)
    lesson = current_lesson(db, user)
    if lesson is None:
        done = todays_lesson(db, user)
        if done is not None:
            raise HTTPException(status_code=409, detail="Ukończonej lekcji nie generuje się od nowa.")
        return {"success": True, "deleted": 0}

    fresh_cards = db.query(Flashcard.id).filter(
        Flashcard.lesson_id == lesson.id,
        (Flashcard.repetitions == 0) | (Flashcard.repetitions == None),  # noqa: E711
        Flashcard.last_review_date == None,  # noqa: E711
    )
    db.query(Flashcard).filter(Flashcard.id.in_(fresh_cards.scalar_subquery())).delete(synchronize_session=False)
    db.query(Flashcard).filter(Flashcard.lesson_id == lesson.id).update(
        {Flashcard.lesson_id: None}, synchronize_session=False)

    answered = db.query(SkillAttempt.exercise_id).filter(SkillAttempt.exercise_id != None)  # noqa: E711
    unused = [r[0] for r in db.query(Exercise.id).filter(
        Exercise.source_lesson_id == lesson.id,
        (Exercise.times_seen == 0) | (Exercise.times_seen == None),  # noqa: E711
        Exercise.id.notin_(answered.scalar_subquery()),
    ).all()]
    if unused:
        db.query(Exercise).filter(Exercise.variant_of.in_(unused)).update(
            {Exercise.variant_of: None}, synchronize_session=False)
        db.query(Exercise).filter(Exercise.id.in_(unused)).delete(synchronize_session=False)
    db.query(Exercise).filter(Exercise.source_lesson_id == lesson.id).update(
        {Exercise.source_lesson_id: None}, synchronize_session=False)

    # SQLite gives the regenerated lesson the same id; its topic links must not carry over
    db.query(TopicItem).filter(TopicItem.item_type == "lesson", TopicItem.item_id == lesson.id).delete(
        synchronize_session=False)
    db.delete(lesson)
    db.commit()
    return {"success": True, "deleted": 1}


@with_model("lesson")
async def _ai_generate_concepts(prompt: str) -> dict:
    return await ai_generate_json(prompt)


@router.post("/api/lessons/{lesson_id}/concept-flashcards")
async def generate_concept_flashcards(lesson_id: int, user_id: int, db: Session = Depends(get_db)):
    """Extract grammar concepts from lesson and create concept flashcards."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify ownership
    if lesson.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this lesson")

    try:
        content = json.loads(lesson.content)
    except (json.JSONDecodeError, TypeError):
        content = {}
    # The generator stores grammar as content["grammar"] = {topic, explanation,
    # rule, examples}. This used to read only top-level "grammar_explanation" /
    # "explanation" keys that are never emitted, so every lesson answered
    # "no grammar" and the "Dodaj koncepcje do fiszek" button never made a card.
    grammar = content.get("grammar") if isinstance(content.get("grammar"), dict) else {}
    grammar_explanation = (
        grammar.get("explanation")
        or content.get("grammar_explanation")
        or content.get("explanation", "")
    )
    topic = grammar.get("topic") or lesson.topic
    language = lesson.language
    cefr_level = lesson.cefr_level

    if not grammar_explanation:
        return {"success": False, "message": "Brak treści gramatycznej w tej lekcji.", "created": 0}

    extra_context = ""
    if grammar.get("rule"):
        extra_context += f"\nRule: {grammar['rule']}"
    example_sentences = [
        ex.get("sentence") or ex.get("text")
        for ex in grammar.get("examples") or []
        if isinstance(ex, dict) and (ex.get("sentence") or ex.get("text"))
    ]
    if example_sentences:
        extra_context += "\nExamples: " + " | ".join(example_sentences[:5])

    # Ask AI to extract key concepts as flashcard pairs
    prompt = f"""From this {language} grammar explanation, extract 3-5 key grammar CONCEPTS as flashcard pairs.
Each flashcard: front = the grammar rule/concept name (in Polish), back = brief explanation + example in {language}.

Grammar topic: {topic}
Explanation: {grammar_explanation[:1200]}{extra_context}

Return JSON:
{{
    "concepts": [
        {{
            "front": "Akkusativ z rodzajnikiem określonym",
            "back": "den (m), die (f), das (n), die (pl)\\nBeispiel: Ich sehe den Mann.",
            "example": "Ich sehe den Mann."
        }}
    ]
}}"""

    try:
        result = await _ai_generate_concepts(prompt)
        concepts = result.get("concepts", [])
    except (httpx.RequestError, ValueError, KeyError):
        return {"success": False, "message": "AI generation failed", "created": 0}

    # N+1 fix: batch-check existing flashcards for all concepts at once
    concept_fronts = [c.get("front", "") for c in concepts if c.get("front") and c.get("back")]
    if concept_fronts:
        existing_fc = db.query(Flashcard.word).filter(
            Flashcard.user_id == lesson.user_id,
            Flashcard.word.in_(concept_fronts)
        ).all()
        concept_existing_words = {row[0] for row in existing_fc}
    else:
        concept_existing_words = set()

    created = 0
    skipped = 0
    for concept in concepts:
        front = concept.get("front", "")
        back = concept.get("back", "")
        if not front or not back:
            continue
        if front not in concept_existing_words:
            fc = Flashcard(
                user_id=lesson.user_id,
                word=front,
                translation=back,
                example_sentence=concept.get("example", ""),
                language=language,
                cefr_level=cefr_level
            )
            db.add(fc)
            created += 1
        else:
            skipped += 1

    db.commit()
    if created == 0 and skipped == 0:
        return {"success": False, "message": "AI nie wygenerowało koncepcji dla tej lekcji. Spróbuj ponownie.", "created": 0}
    return {"success": True, "created": created, "skipped": skipped, "total_concepts": len(concepts)}


@router.get("/api/lessons/latest/{user_id}/concepts")
async def get_lesson_concepts(user_id: int, db: Session = Depends(get_db)):
    """Generate grammar concepts from the latest lesson and return them (without saving to flashcards)."""
    user = get_user_or_404(db, user_id)

    # The lesson just studied, not the prepared next one (A10)
    lesson = lesson_for_review(db, user)

    if not lesson:
        return {"concepts": [], "lesson_title": None}

    content = json.loads(lesson.content)
    # Daily lessons keep grammar under "grammar"; the old keys alone gave nothing (01.11.2026)
    grammar_explanation = lesson_grammar_text(content)
    if not grammar_explanation:
        return {"concepts": [], "lesson_title": lesson.title}

    prompt = f"""From this {lesson.language} grammar explanation, extract 3-6 key grammar CONCEPTS.
Each concept: name (in Polish), brief explanation (in Polish), example in {lesson.language}.

Grammar topic: {lesson.topic}
Explanation: {grammar_explanation[:800]}

Return JSON:
{{
    "concepts": [
        {{
            "name": "Akkusativ z rodzajnikiem określonym",
            "explanation": "Zmiana rodzajnika dla przypadku Akkusativ.",
            "example": "Ich sehe den Mann."
        }}
    ]
}}"""

    try:
        result = await _ai_generate_concepts(prompt)
        concepts = result.get("concepts", [])
    except (httpx.RequestError, ValueError, KeyError):
        concepts = []

    return {
        "concepts": concepts,
        "lesson_title": lesson.title,
        "lesson_id": lesson.id,
        "topic": lesson.topic,
    }


@router.get("/api/lessons/study-plan/{user_id}")
async def get_study_plan(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)

    active_plan = db.query(StudyPlan).filter(
        StudyPlan.user_id == user_id,
        StudyPlan.is_active == True
    ).first()

    if not active_plan:
        return {"plan": None, "current_lesson": None}

    import json as _json
    try:
        plan_data = _json.loads(active_plan.plan_data)
    except (json.JSONDecodeError, TypeError):
        plan_data = {}

    # Also get current lesson number
    latest_lesson = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language
    ).order_by(Lesson.day_number.desc()).first()

    return {
        "plan": plan_data,
        "current_lesson": latest_lesson.day_number if latest_lesson else 0,
        "cefr_level": active_plan.cefr_level,
        "language": active_plan.language
    }


@with_model("lesson")
async def _ai_evaluate_production(prompt: str) -> dict:
    return await ai_generate_json(prompt)


@router.post("/api/lessons/{lesson_id}/evaluate-production")
async def evaluate_production_task(
    lesson_id: int,
    request: EvaluateProductionRequest,
    db: Session = Depends(get_db)
):
    if not request.user_answer or not request.user_answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty")

    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify ownership
    if request.user_id and lesson.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this lesson")

    prompt = f"""You are a {request.language} language teacher. Evaluate this student's answer.

Level: {request.cefr_level}
Task instruction: {request.instruction}
Student's answer: {request.user_answer}

Evaluate the answer and return ONLY valid JSON:
{{
    "score": 85,
    "feedback": "Detailed feedback in Polish",
    "corrections": [
        {{"error": "mistake in student text", "correction": "correct form"}}
    ],
    "improved_version": "Improved version of their text in {request.language}"
}}

Score 0-100. Corrections array can be empty if there are no errors. Write feedback in Polish."""

    try:
        result = await _ai_evaluate_production(prompt)
        return {
            "success": True,
            "score": result.get("score", 0),
            "feedback": result.get("feedback", ""),
            "corrections": result.get("corrections", []),
            "improved_version": result.get("improved_version", "")
        }
    except Exception as e:
        logger.error(f"Error evaluating production task: {e}")
        return {
            "success": False,
            "score": 0,
            "feedback": "Nie udało się ocenić odpowiedzi. Spróbuj ponownie.",
            "corrections": [],
            "improved_version": ""
        }
