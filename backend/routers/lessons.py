import json
import logging
import os
from datetime import date, datetime, timedelta, timezone

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
from backend.models.topic import Topic
from backend.models.user import User
from backend.schemas.lesson import (
    CompleteLessonRequest,
    EvaluateProductionRequest,
    ExerciseErrorRequest,
)
from backend.services.audio_service import (
    generate_full_lesson_audio,
    generate_lesson_package_audio,
    generate_vocabulary_audio,
)
from backend.services.exercise_service import create_exercises_from_lesson
from backend.services.flashcard_service import create_flashcards_from_vocab
from backend.services.gemini_service import generate_json as ai_generate_json
from backend.services.gemini_service import with_model
from backend.services.lesson_generator import (
    generate_daily_lesson,
    generate_iplus1_content,
)
from backend.services.obsidian_service import save_obsidian_md
from backend.services.pdf_service import EXPORTS_DIR, generate_lesson_pdf
from backend.services.streak_service import calculate_streak
from backend.services.sync_service import already_applied, parse_occurred_at, record_event
from backend.services.topic_service import process_lesson_topics_bg
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)

router = APIRouter()


def get_day_number(user: User, db: Session = None, language: str = None) -> int:
    """Calculate which day number the user is on for a specific language.
    Uses per-language lesson count so each language starts at day 1."""
    if db is not None and language is not None:
        count = db.query(Lesson).filter(
            Lesson.user_id == user.id,
            Lesson.language == language,
            Lesson.is_completed == True
        ).count()
        return count + 1
    # Fallback: global calendar-based calculation
    if not user.created_at:
        return 1
    delta = date.today() - user.created_at.date()
    return max(1, delta.days + 1)


def get_recent_errors(user_id: int, db: Session, limit: int = 10) -> list:
    """Get recent test errors for the user."""
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


@router.get("/api/lessons/today/{user_id}")
async def get_today_lesson(user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)

    # Check if today's lesson already exists for this language
    from sqlalchemy import func
    today_date = date.today()
    existing_lesson = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language,
        func.date(Lesson.created_at) == today_date
    ).first()

    # If no lesson today, check for uncompleted lesson from previous days
    if not existing_lesson:
        existing_lesson = db.query(Lesson).filter(
            Lesson.user_id == user_id,
            Lesson.language == user.target_language,
            Lesson.is_completed == False
        ).order_by(Lesson.created_at.desc()).first()

    day_number = get_day_number(user, db, user.target_language)

    if existing_lesson:
        content = json.loads(existing_lesson.content)
        return {
            "lesson_id": existing_lesson.id,
            "day_number": existing_lesson.day_number,
            "title": existing_lesson.title,
            "topic": existing_lesson.topic,
            "content": content,
            "is_completed": existing_lesson.is_completed,
            "language": existing_lesson.language,
            "cefr_level": existing_lesson.cefr_level,
            "created_at": existing_lesson.created_at.isoformat()
        }

    # Get active study plan
    study_plan = db.query(StudyPlan).filter(
        StudyPlan.user_id == user_id,
        StudyPlan.is_active == True
    ).first()

    if not study_plan:
        raise HTTPException(status_code=404, detail="No active study plan. Please complete placement test first.")

    study_plan_data = json.loads(study_plan.plan_data)

    # Get recent errors to incorporate in lesson
    user_errors = get_recent_errors(user_id, db)

    # Get recent topics for interleaving (last 7 days)
    week_ago = datetime.combine(date.today() - timedelta(days=7), datetime.min.time())
    recent_lessons = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.created_at >= week_ago
    ).order_by(Lesson.created_at.desc()).limit(7).all()
    recent_topics = [l.topic for l in recent_lessons if l.topic] if recent_lessons else None

    # ── RAG: fetch user's data to personalize the lesson ──

    # User's known vocabulary (flashcards) — 50 cards, genuinely-known first.
    # SCI-1: mastered words (3 correct recalls across sessions) are the most
    # reliable "known" input for i+1 comprehensible-input generation.
    user_flashcards = db.query(Flashcard.word).filter(
        Flashcard.user_id == user_id,
        Flashcard.language == user.target_language,
        Flashcard.is_active == True,
    ).order_by(Flashcard.is_mastered.desc(), Flashcard.created_at.desc()).limit(50).all()
    user_vocabulary = [f[0] for f in user_flashcards] if user_flashcards else None

    # Weak topics (low memory_strength) and strong topics (high memory_strength)
    all_topics = db.query(Topic).filter(
        Topic.user_id == user_id,
        Topic.language == user.target_language,
    ).order_by(Topic.memory_strength.asc()).all()

    weak_topics = [t.name for t in all_topics if t.memory_strength < 0.5][:5] if all_topics else None
    strong_topics = [t.name for t in reversed(all_topics) if t.memory_strength >= 0.7][:3] if all_topics else None

    # Generate new lesson
    lesson_content = await generate_daily_lesson(
        user_id=user_id,
        target_language=user.target_language,
        native_language=user.native_language,
        cefr_level=user.cefr_level,
        recent_topics=recent_topics,
        day_number=day_number,
        db=db,
        study_plan_data=study_plan_data,
        user_errors=user_errors,
        user_vocabulary=user_vocabulary,
        weak_topics=weak_topics,
        strong_topics=strong_topics,
    )

    # Save lesson to DB (handle race condition via unique constraint)
    lesson = Lesson(
        user_id=user_id,
        day_number=day_number,
        title=lesson_content.get("title", f"Dzień {day_number}"),
        topic=lesson_content.get("topic", "General"),
        content=json.dumps(lesson_content),
        cefr_level=user.cefr_level,
        language=user.target_language,
        is_completed=False
    )
    db.add(lesson)
    try:
        db.commit()
        db.refresh(lesson)
    except IntegrityError:
        # Another concurrent request already created this lesson — rollback and use existing
        db.rollback()
        from sqlalchemy import func as _func
        existing_lesson = db.query(Lesson).filter(
            Lesson.user_id == user_id,
            Lesson.language == user.target_language,
            _func.date(Lesson.created_at) == date.today()
        ).first()
        if existing_lesson:
            content = json.loads(existing_lesson.content)
            return {
                "lesson_id": existing_lesson.id,
                "day_number": existing_lesson.day_number,
                "title": existing_lesson.title,
                "topic": existing_lesson.topic,
                "content": content,
                "is_completed": existing_lesson.is_completed,
                "language": existing_lesson.language,
                "cefr_level": existing_lesson.cefr_level,
                "created_at": existing_lesson.created_at.isoformat()
            }
        raise

    # Extract vocabulary and create flashcards
    create_flashcards_from_vocab(
        db, lesson_content.get("vocabulary", []),
        user_id, user.target_language, user.cefr_level,
        lesson.id, lesson.day_number, lesson.topic
    )
    # Persist exercises into the reusable bank (spaced retrieval + interleaving)
    create_exercises_from_lesson(
        db, lesson_content, user_id, user.target_language,
        user.cefr_level, lesson.id, lesson.topic
    )
    db.commit()

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

    return {
        "lesson_id": lesson.id,
        "day_number": lesson.day_number,
        "title": lesson.title,
        "topic": lesson.topic,
        "content": lesson_content,
        "is_completed": lesson.is_completed,
        "language": lesson.language,
        "cefr_level": lesson.cefr_level,
        "created_at": lesson.created_at.isoformat()
    }


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

    content = json.loads(lesson.content)
    return {
        "lesson_id": lesson.id,
        "day_number": lesson.day_number,
        "title": lesson.title,
        "topic": lesson.topic,
        "content": content,
        "is_completed": lesson.is_completed,
        "language": lesson.language,
        "cefr_level": lesson.cefr_level,
        "created_at": lesson.created_at.isoformat()
    }


@router.post("/api/lessons/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: int,
    request: CompleteLessonRequest,
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

        # Award XP for completing lesson
        if request.user_id:
            user = db.query(User).filter(User.id == request.user_id).first()
            if user:
                user.total_xp += 25  # 25 XP for completing a lesson
                xp_awarded = 25
                # Update streak — consecutive days with at least one completed lesson (with freeze support)
                streak, freezes_left = calculate_streak(db, user.id, user.streak_freezes)
                user.streak_days = streak
                user.streak_freezes = freezes_left

        record_event(db, request.client_event_id,
                     request.user_id or lesson.user_id,
                     "lesson_complete", lesson.id, occurred)

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

        # Check achievements after commit
        if request.user_id:
            from backend.services.achievement_service import check_and_award_achievements
            user = db.query(User).filter(User.id == request.user_id).first()
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
    audio_files = await generate_lesson_package_audio(content, lesson.language, lesson_id)

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
    """Generate the NEXT lesson (max day_number + 1) without deleting the current one."""
    user = get_user_or_404(db, user_id)

    # Get active study plan
    study_plan = db.query(StudyPlan).filter(
        StudyPlan.user_id == user_id,
        StudyPlan.is_active == True
    ).first()
    if not study_plan:
        raise HTTPException(status_code=404, detail="No active study plan. Please complete placement test first.")

    study_plan_data = json.loads(study_plan.plan_data)

    # Determine next day number (per-language)
    latest_lesson = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language
    ).order_by(Lesson.day_number.desc()).first()
    next_day = (latest_lesson.day_number + 1) if latest_lesson else 1

    # Get recent errors
    user_errors = get_recent_errors(user_id, db)

    # Get recent topics for interleaving
    week_ago = datetime.combine(date.today() - timedelta(days=7), datetime.min.time())
    recent_lessons = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.created_at >= week_ago
    ).order_by(Lesson.created_at.desc()).limit(7).all()
    recent_topics = [l.topic for l in recent_lessons if l.topic] if recent_lessons else None

    # Get exercise errors from recent lessons to pass to prompt
    exercise_errors = []
    if latest_lesson and latest_lesson.content:
        try:
            latest_content = json.loads(latest_lesson.content)
            exercise_errors = latest_content.get("user_exercise_errors", [])
        except (json.JSONDecodeError, TypeError):
            pass

    # RAG: fetch user's vocabulary and topic strengths for next lesson too
    # SCI-1: mastered words first (most reliable "known" input for i+1).
    next_flashcards = db.query(Flashcard.word).filter(
        Flashcard.user_id == user_id,
        Flashcard.language == user.target_language,
        Flashcard.is_active == True,
    ).order_by(Flashcard.is_mastered.desc(), Flashcard.created_at.desc()).limit(50).all()
    next_vocab = [f[0] for f in next_flashcards] if next_flashcards else None

    next_all_topics = db.query(Topic).filter(
        Topic.user_id == user_id,
        Topic.language == user.target_language,
    ).order_by(Topic.memory_strength.asc()).all()
    next_weak = [t.name for t in next_all_topics if t.memory_strength < 0.5][:5] if next_all_topics else None
    next_strong = [t.name for t in reversed(next_all_topics) if t.memory_strength >= 0.7][:3] if next_all_topics else None

    # Generate lesson
    lesson_content = await generate_daily_lesson(
        user_id=user_id,
        day_number=next_day,
        study_plan_data=study_plan_data,
        user_errors=user_errors + exercise_errors,
        cefr_level=user.cefr_level,
        target_language=user.target_language,
        native_language=user.native_language,
        recent_topics=recent_topics,
        user_vocabulary=next_vocab,
        weak_topics=next_weak,
        strong_topics=next_strong,
        db=db,
    )

    # Save lesson to DB
    lesson = Lesson(
        user_id=user_id,
        day_number=next_day,
        title=lesson_content.get("title", f"Dzień {next_day}"),
        topic=lesson_content.get("topic", "General"),
        content=json.dumps(lesson_content),
        cefr_level=user.cefr_level,
        language=user.target_language,
        is_completed=False
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    # Create flashcards from vocabulary
    create_flashcards_from_vocab(
        db, lesson_content.get("vocabulary", []),
        user_id, user.target_language, user.cefr_level,
        lesson.id, lesson.day_number, lesson.topic
    )
    # Persist exercises into the reusable bank
    create_exercises_from_lesson(
        db, lesson_content, user_id, user.target_language,
        user.cefr_level, lesson.id, lesson.topic
    )
    db.commit()

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

    return {
        "lesson_id": lesson.id,
        "day_number": lesson.day_number,
        "title": lesson.title,
        "topic": lesson.topic,
        "content": lesson_content,
        "is_completed": lesson.is_completed,
        "language": lesson.language,
        "cefr_level": lesson.cefr_level,
        "created_at": lesson.created_at.isoformat()
    }


@router.post("/api/lessons/{lesson_id}/exercise-error")
async def record_exercise_error(
    lesson_id: int,
    request: ExerciseErrorRequest,
    db: Session = Depends(get_db)
):
    """Record an exercise error into the lesson's content blob (user_exercise_errors list)."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Verify ownership
    if request.user_id and lesson.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this lesson")

    try:
        content = json.loads(lesson.content)
    except (json.JSONDecodeError, TypeError):
        content = {}

    errors = content.get("user_exercise_errors", [])
    errors.append({
        "question": request.question,
        "user_answer": request.user_answer,
        "correct_answer": request.correct_answer,
        "exercise_type": request.exercise_type,
    })
    content["user_exercise_errors"] = errors
    lesson.content = json.dumps(content)
    db.commit()

    return {"success": True, "total_errors": len(errors)}


@router.delete("/api/lessons/reset-today/{user_id}")
async def reset_today_lesson(user_id: int, db: Session = Depends(get_db)):
    """Delete today's lesson so it gets regenerated on next visit."""
    from backend.models.flashcard import Flashcard
    user = get_user_or_404(db, user_id)
    today_start = datetime.combine(date.today(), datetime.min.time())
    lessons_to_delete = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language,
        Lesson.created_at >= today_start
    ).all()
    lesson_ids = [l.id for l in lessons_to_delete]
    # Remove child flashcards first (FK constraint, no ON DELETE CASCADE in SQLite)
    if lesson_ids:
        db.query(Flashcard).filter(Flashcard.lesson_id.in_(lesson_ids)).delete(
            synchronize_session=False
        )
    deleted = db.query(Lesson).filter(Lesson.id.in_(lesson_ids)).delete(
        synchronize_session=False
    ) if lesson_ids else 0
    db.commit()
    return {"success": True, "deleted": deleted}


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
    # lesson content stores grammar as "explanation" (frontend uses content.explanation)
    grammar_explanation = content.get("grammar_explanation") or content.get("explanation", "")
    topic = lesson.topic
    language = lesson.language
    cefr_level = lesson.cefr_level

    if not grammar_explanation:
        return {"success": False, "message": "Brak treści gramatycznej w tej lekcji.", "created": 0}

    # Ask AI to extract key concepts as flashcard pairs
    prompt = f"""From this {language} grammar explanation, extract 3-5 key grammar CONCEPTS as flashcard pairs.
Each flashcard: front = the grammar rule/concept name (in Polish), back = brief explanation + example in {language}.

Grammar topic: {topic}
Explanation: {grammar_explanation[:800]}

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

    lesson = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language
    ).order_by(Lesson.day_number.desc()).first()

    if not lesson:
        return {"concepts": [], "lesson_title": None}

    content = json.loads(lesson.content)
    grammar_explanation = content.get("grammar_explanation") or content.get("explanation", "")
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
