import logging
import os
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.exercise import Exercise
from backend.models.lesson import Lesson
from backend.models.test_result import TestResult
from backend.services.audio_service import AUDIO_DIR, generate_audio
from backend.services.dictation_service import (
    diff_transcription,
    generate_dictation_sentences,
)
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)
router = APIRouter()


class DictationCheckRequest(BaseModel):
    reference: str
    typed: str


@router.get("/api/quickmode/{user_id}")
async def get_quickmode_plan(user_id: int, db: Session = Depends(get_db)):
    """Return a prioritized 15-minute daily activity list."""
    user = get_user_or_404(db, user_id)

    activities = []

    # Check today's lesson (per language)
    from sqlalchemy import func
    today_date = date.today()
    today_lesson = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language,
        func.date(Lesson.created_at) == today_date
    ).first()

    if today_lesson and not today_lesson.is_completed:
        activities.append({
            "id": "lesson",
            "title": "Dzisiejsza lekcja",
            "description": today_lesson.title,
            "estimated_minutes": 8,
            "priority": 1,
            "route": "/lesson",
            "icon": "BookOpen",
            "completed": False,
        })
    elif today_lesson and today_lesson.is_completed:
        # Check if test done today
        today_test = db.query(TestResult).filter(
            TestResult.user_id == user_id,
            func.date(TestResult.created_at) == today_date
        ).first()
        if not today_test:
            activities.append({
                "id": "test",
                "title": "Dzienny test",
                "description": "Sprawdź wiedzę z dzisiejszej lekcji",
                "estimated_minutes": 5,
                "priority": 1,
                "route": "/test",
                "icon": "FlaskConical",
                "completed": False,
            })
        else:
            activities.append({
                "id": "test",
                "title": "Dzienny test",
                "description": "Już ukończono dziś",
                "estimated_minutes": 5,
                "priority": 3,
                "route": "/test",
                "icon": "FlaskConical",
                "completed": True,
            })
    else:
        activities.append({
            "id": "lesson",
            "title": "Dzisiejsza lekcja",
            "description": "Zacznij dzienną lekcję",
            "estimated_minutes": 8,
            "priority": 1,
            "route": "/lesson",
            "icon": "BookOpen",
            "completed": False,
        })

    # Pronunciation practice
    activities.append({
        "id": "pronunciation",
        "title": "Ćwiczenie wymowy",
        "description": "Ćwicz wymowę i sprawdź poprawność",
        "estimated_minutes": 3,
        "priority": 3,
        "route": "/pronunciation",
        "icon": "Mic",
        "completed": False,
    })

    # News reading
    activities.append({
        "id": "news",
        "title": "Newsy w języku docelowym",
        "description": f"Czytaj uproszczone wiadomości po {user.target_language}",
        "estimated_minutes": 3,
        "priority": 4,
        "route": "/news",
        "icon": "Newspaper",
        "completed": False,
    })

    # Exercise bank: spaced + interleaved practice from previously generated items
    due_exercises = db.query(Exercise).filter(
        Exercise.user_id == user_id,
        Exercise.language == user.target_language,
        Exercise.is_active == True,  # noqa: E712
        Exercise.next_review_date <= datetime.now(timezone.utc),
    ).count()
    if due_exercises:
        activities.append({
            "id": "practice",
            "title": "Ćwiczenia do powtórki",
            "description": f"{due_exercises} zadań czeka na powtórkę",
            "estimated_minutes": 5,
            "priority": 2,
            "route": "/practice",
            "icon": "Dumbbell",
            "completed": False,
        })

    # Dictation (SCI-6): listen and type what you hear
    activities.append({
        "id": "dictation",
        "title": "Dyktando ze słuchu",
        "description": "Posłuchaj zdania i zapisz je ze słuchu",
        "estimated_minutes": 4,
        "priority": 4,
        "route": "/dictation",
        "icon": "Headphones",
        "completed": False,
    })

    # Read aloud (SCI-7, production effect): repeat new words out loud
    activities.append({
        "id": "read-aloud",
        "title": "Powtórz na głos",
        "description": "Posłuchaj nowych słów i powtórz je głośno",
        "estimated_minutes": 2,
        "priority": 3,
        "route": "/read-aloud",
        "icon": "Volume2",
        "completed": False,
    })

    # Sort by priority
    activities.sort(key=lambda x: x["priority"])

    total_minutes = sum(a["estimated_minutes"] for a in activities if not a["completed"])

    return {
        "user_id": user_id,
        "target_language": user.target_language,
        "cefr_level": user.cefr_level,
        "total_estimated_minutes": total_minutes,
        "activities": activities,
        "timer_minutes": 15,
    }


@router.get("/api/quickmode/dictation/{user_id}")
async def get_dictation(user_id: int, count: int = 3, db: Session = Depends(get_db)):
    """SCI-6: generate dictation sentences (with audio) for the learner's level."""
    user = get_user_or_404(db, user_id)
    sentences = await generate_dictation_sentences(
        target_language=user.target_language,
        cefr_level=user.cefr_level,
        count=count,
    )

    items = []
    for i, sentence in enumerate(sentences):
        audio_path = None
        # Filename derived from content so identical sentences reuse cached audio
        safe = "".join(c for c in sentence[:24] if c.isalnum() or c == " ").strip().replace(" ", "_")
        filename = f"dictation_{user_id}_{i}_{safe}.mp3"
        output_path = os.path.join(AUDIO_DIR, filename)
        try:
            if not os.path.exists(output_path):
                await generate_audio(sentence, user.target_language, output_path)
            audio_path = f"/audio/{filename}"
        except Exception as e:
            logger.warning(f"Dictation audio failed for '{sentence[:20]}...': {e}")
        items.append({"sentence": sentence, "audio_path": audio_path})

    return {
        "user_id": user_id,
        "target_language": user.target_language,
        "cefr_level": user.cefr_level,
        "items": items,
    }


@router.post("/api/quickmode/dictation/check")
async def check_dictation(payload: DictationCheckRequest):
    """SCI-6: word-level diff between the reference sentence and what the user typed."""
    return diff_transcription(payload.reference, payload.typed)


# ── SCI-7: Production effect — read new words ALOUD ─────────────────────
# MacLeod et al. (2010, RCT): words read aloud are remembered better than
# words read silently. v1: no speech recognition — self-assessment only.

@router.get("/api/quickmode/read-aloud/{user_id}")
async def get_read_aloud(user_id: int, count: int = 8, db: Session = Depends(get_db)):
    """Newest flashcards as a read-aloud deck: hear TTS, repeat aloud, self-check.

    Source: the user's most recently created active flashcards (the freshest
    vocabulary, before FSRS spaces it out). Each item carries cached TTS audio
    so repeating works offline-ish and doesn't re-synthesize on every visit.
    """
    from backend.models.flashcard import Flashcard

    user = get_user_or_404(db, user_id)
    count = max(1, min(count, 20))

    cards = (
        db.query(Flashcard)
        .filter(
            Flashcard.user_id == user_id,
            Flashcard.language == user.target_language,
            Flashcard.is_active == True,  # noqa: E712
        )
        .order_by(Flashcard.id.desc())
        .limit(count)
        .all()
    )

    items = []
    for i, card in enumerate(cards):
        text = card.word
        audio_path = card.audio_path
        if not audio_path:
            safe = "".join(c for c in text[:24] if c.isalnum() or c == " ").strip().replace(" ", "_")
            filename = f"readaloud_{user_id}_{card.id}_{safe}.mp3"
            output_path = os.path.join(AUDIO_DIR, filename)
            try:
                if not os.path.exists(output_path):
                    await generate_audio(text, user.target_language, output_path)
                audio_path = f"/audio/{filename}"
                card.audio_path = audio_path
            except Exception as e:
                logger.warning("Read-aloud TTS failed for card %s: %s", card.id, e)
        items.append(
            {
                "flashcard_id": card.id,
                "word": card.word,
                "translation": card.translation,
                "example_sentence": card.example_sentence,
                "audio_path": audio_path,
            }
        )
    db.commit()

    return {
        "user_id": user_id,
        "target_language": user.target_language,
        "cefr_level": user.cefr_level,
        "items": items,
        "instruction": "Posłuchaj słowa, powtórz je NA GŁOS, potem oceń sam siebie.",
    }
