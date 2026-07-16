import csv
import io
import json
import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.flashcard import Flashcard
from backend.schemas.flashcard import (
    AddFlashcardAIRequest,
    AddFlashcardRequest,
    GenerateFromTopicRequest,
    ReviewFlashcardRequest,
)
from backend.services.achievement_service import check_and_award_achievements
from backend.services.anki_service import generate_anki_deck
from backend.services.audio_service import generate_flashcard_audio
from backend.services.fsrs_service import apply_fsrs as fsrs_apply
from backend.services.gemini_service import generate_json, with_model
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/flashcards/{user_id}")
async def get_flashcards(
    user_id: int,
    active_only: bool = True,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, user_id)

    query = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.language == user.target_language
    )
    if active_only:
        query = query.filter(Flashcard.is_active == True)

    total = query.count()
    flashcards = query.order_by(Flashcard.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "flashcards": [
            {
                "id": f.id,
                "word": f.word,
                "translation": f.translation,
                "example_sentence": f.example_sentence,
                "audio_path": f.audio_path,
                "language": f.language,
                "cefr_level": f.cefr_level,
                "difficulty": f.difficulty,
                "stability": f.stability,
                "retrievability": f.retrievability,
                "interval_days": f.interval_days,
                "repetitions": f.repetitions,
                "lapses": f.lapses,
                "fsrs_state": f.fsrs_state,
                "next_review_date": f.next_review_date.isoformat() if f.next_review_date else None,
                "created_at": f.created_at.isoformat(),
                "lesson_id": f.lesson_id,
                "lesson_day": f.lesson_day,
                "lesson_topic": f.lesson_topic,
                "gender": f.gender,
                "isImportant": f.isImportant,
            }
            for f in flashcards
        ],
        "total": total
    }


@router.get("/api/flashcards/{user_id}/due")
async def get_due_flashcards(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)

    now = datetime.now(timezone.utc)
    due_cards = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.language == user.target_language,
        Flashcard.is_active == True,
        Flashcard.next_review_date <= now
    ).order_by(Flashcard.next_review_date.asc()).all()

    return {
        "due_cards": [
            {
                "id": f.id,
                "word": f.word,
                "translation": f.translation,
                "example_sentence": f.example_sentence,
                "audio_path": f.audio_path,
                "difficulty": f.difficulty,
                "stability": f.stability,
                "interval_days": f.interval_days,
                "fsrs_state": f.fsrs_state,
            }
            for f in due_cards
        ],
        "count": len(due_cards)
    }


@router.post("/api/flashcards/{flashcard_id}/review")
async def review_flashcard(
    flashcard_id: int,
    request: ReviewFlashcardRequest,
    user_id: int,
    db: Session = Depends(get_db)
):
    flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    # Verify ownership
    if flashcard.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to review this flashcard")

    user = get_user_or_404(db, user_id)

    # Determine session type based on current UTC hour
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    if 6 <= current_hour <= 10:
        session_type = "morning"
    elif 20 <= current_hour <= 22:
        session_type = "evening"
    else:
        session_type = "day"

    # ── NEURO-11: read the user's most recent sleep quality ──
    sleep_quality = None
    if user.sleep_data:
        try:
            import json as _json
            sd = _json.loads(user.sleep_data)
            sleep_quality = sd.get("last_sleep_quality")
        except (json.JSONDecodeError, TypeError):
            sleep_quality = None

    # ── NEURO-12: interleaving bonus (topic variety among due cards) ──
    # A diverse due-queue (more distinct lesson topics) strengthens
    # desirable-difficulties / spacing effect → small bonus per review.
    due_cards = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.language == user.target_language,
        Flashcard.is_active == True,
        Flashcard.next_review_date <= now,
        Flashcard.id != flashcard_id,
    ).all()
    due_topics = {c.lesson_topic for c in due_cards if c.lesson_topic}
    # Bonus scales with how many *different* topics are queued alongside this card
    interleaving_bonus = round(min(1.0, len(due_topics) / 10.0), 3)

    # ── NEURO-13: interference penalty (same-topic cards competing) ──
    # Cards sharing the exact lesson topic compete for the same neural trace.
    same_topic_count = sum(
        1 for c in due_cards if c.lesson_topic and c.lesson_topic == flashcard.lesson_topic
    )
    interference_penalty = round(min(0.3, (same_topic_count) / 5.0 * 0.3), 3)

    # Prepare FSRS card state from flashcard (uses the same v6 lib as topics)
    result = fsrs_apply(
        rating=request.rating,
        difficulty=flashcard.difficulty,
        stability=flashcard.stability,
        retrievability=flashcard.retrievability if flashcard.retrievability > 0 else None,
        elapsed_days=0,
        reps=flashcard.repetitions,
        lapses=flashcard.lapses or 0,
        current_state=flashcard.fsrs_state or "Learning",
        last_review_date=flashcard.last_review_date,
    )

    # Update flashcard with FSRS v6 results
    flashcard.difficulty = result.difficulty
    flashcard.stability = result.stability
    flashcard.retrievability = result.retrievability
    flashcard.interval_days = result.interval
    flashcard.repetitions = result.repetitions
    flashcard.lapses = result.lapses
    flashcard.fsrs_state = result.state
    flashcard.next_review_date = result.next_review_date
    flashcard.last_review_date = now
    # Preserve neuro telemetry metadata (informational only, not used by FSRS scheduler)
    flashcard.session_type = session_type
    flashcard.sleep_quality = sleep_quality
    flashcard.interleaving_bonus = interleaving_bonus
    flashcard.interference_penalty = interference_penalty

    db.commit()

    # Check achievements after flashcard review (e.g. flashcards_review_50)
    new_achievements = check_and_award_achievements(user, db)

    return {
        "success": True,
        "flashcard_id": flashcard_id,
        "new_interval": result.interval,
        "new_difficulty": result.difficulty,
        "new_stability": result.stability,
        "state": getattr(result, 'state', "Review"),
        "next_review": flashcard.next_review_date.isoformat(),
        "sleep_quality": sleep_quality,
        "interleaving_bonus": interleaving_bonus,
        "interference_penalty": interference_penalty,
        "new_achievements": new_achievements,
    }


@router.post("/api/flashcards/{user_id}/export-anki")
async def export_anki(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)

    flashcards = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.language == user.target_language,
        Flashcard.is_active == True
    ).all()

    if not flashcards:
        raise HTTPException(status_code=404, detail="No flashcards found to export")

    try:
        deck_path = generate_anki_deck(
            flashcards=flashcards,
            language=user.target_language,
            user_name=user.name
        )

        return FileResponse(
            path=deck_path,
            filename=os.path.basename(deck_path),
            media_type="application/octet-stream"
        )
    except (IOError, OSError, ValueError) as e:
        logger.exception("Error exporting Anki deck: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate Anki deck")


@router.post("/api/flashcards/{flashcard_id}/audio")
async def generate_audio(flashcard_id: int, user_id: int, db: Session = Depends(get_db)):
    flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    # Verify ownership
    if flashcard.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this flashcard")

    try:
        audio_path = await generate_flashcard_audio(
            word=flashcard.word,
            language=flashcard.language,
            flashcard_id=flashcard_id
        )
        if audio_path:
            flashcard.audio_path = audio_path
            db.commit()

        return {"success": True, "audio_path": audio_path}
    except httpx.RequestError as e:
        logger.error(f"Audio service error: {e}")
        raise HTTPException(status_code=503, detail="Audio service unavailable")
    except Exception:
        logger.exception("Unexpected error generating flashcard audio")
        raise HTTPException(status_code=500, detail="Failed to generate audio")


@router.post("/api/flashcards/{user_id}/add")
async def add_flashcard(
    user_id: int,
    request: AddFlashcardRequest,
    db: Session = Depends(get_db)
):
    user = get_user_or_404(db, user_id)

    # Check for duplicate (per language)
    existing = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.word == request.word,
        Flashcard.language == user.target_language
    ).first()

    if existing:
        return {"success": False, "message": f"Fiszka '{request.word}' już istnieje w Twojej kolekcji.", "id": existing.id}

    flashcard = Flashcard(
        user_id=user_id,
        word=request.word,
        translation=request.translation,
        example_sentence=request.example_sentence,
        language=user.target_language,
        cefr_level=user.cefr_level,
        isImportant=request.isImportant
    )
    db.add(flashcard)
    db.commit()
    db.refresh(flashcard)

    return {"success": True, "id": flashcard.id, "message": "Flashcard added successfully"}


@with_model("lesson")
async def _ai_validate_spelling(prompt: str) -> dict:
    return await generate_json(prompt, fallback={})


@with_model("lesson")
async def _ai_generate_flashcard(prompt: str) -> dict:
    return await generate_json(prompt, fallback={})


@router.post("/api/flashcards/{user_id}/add-ai")
async def add_flashcard_ai(
    user_id: int,
    request: AddFlashcardAIRequest,
    db: Session = Depends(get_db)
):
    user = get_user_or_404(db, user_id)

    # Check for duplicate (per language)
    existing = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.word == request.word,
        Flashcard.language == user.target_language
    ).first()

    if existing:
        return {"success": False, "message": f"Fiszka '{request.word}' już istnieje w Twojej kolekcji.", "id": existing.id}

    # Validate spelling before adding
    validation_prompt = f"""Is '{request.word}' a correctly spelled {user.target_language} word or phrase?
Return ONLY valid JSON:
{{
    "valid": true/false,
    "correction": "corrected form if invalid, empty string if valid"
}}
"""
    try:
        val = await _ai_validate_spelling(validation_prompt)
        if isinstance(val, dict) and val.get("valid") is False:
            correction = val.get("correction", "").strip()
            msg = f"Niepoprawna pisownia."
            if correction:
                msg = f'Niepoprawna pisownia. Czy chodziło Ci o: "{correction}"?'
            return {"success": False, "message": msg}
    except (ValueError, KeyError, TypeError):
        pass  # If validation fails, proceed anyway

    # Use AI to generate translation and example
    prompt = f"""Given the {user.target_language} word or phrase '{request.word}', provide:
- ONE main Polish translation (the most common/primary meaning only — do NOT list all conjugated forms)
- An example sentence in {user.target_language} (at {user.cefr_level} level)
- Polish translation of that example sentence

Return ONLY valid JSON:
{{
    "translation": "single main Polish translation",
    "example": "Example sentence in {user.target_language}",
    "example_translation": "Polish translation of the example"
}}
"""
    translation = ""
    example = ""
    try:
        ai_result = await _ai_generate_flashcard(prompt)
        # Handle both direct dict and nested formats
        if isinstance(ai_result, dict):
            translation = (
                ai_result.get("translation") or
                ai_result.get("polish_translation") or
                ai_result.get("meaning") or ""
            )
            example = (
                ai_result.get("example") or
                ai_result.get("example_sentence") or
                ai_result.get("sentence") or ""
            )
            # If translation is a dict (nested), try to extract string
            if isinstance(translation, dict):
                translation = translation.get("polish", "") or str(translation)
            if isinstance(example, dict):
                example = example.get("sentence", "") or str(example)
            translation = str(translation).strip()
            example = str(example).strip()
    except Exception as e:
        logger.warning(f"AI flashcard generation failed: {e}")
        translation = ""
        example = ""

    flashcard = Flashcard(
        user_id=user_id,
        word=request.word,
        translation=translation,
        example_sentence=example,
        language=user.target_language,
        cefr_level=user.cefr_level
    )
    db.add(flashcard)
    db.commit()
    db.refresh(flashcard)

    return {
        "success": True,
        "id": flashcard.id,
        "word": flashcard.word,
        "translation": translation,
        "example": example,
        "message": "Flashcard added with AI"
    }


@router.post("/api/flashcards/{user_id}/bulk-import")
async def bulk_import_flashcards(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Import flashcards from a CSV/TSV file. Columns: word, translation, example (optional)."""
    user = get_user_or_404(db, user_id)

    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".tsv", ".txt")):
        raise HTTPException(status_code=400, detail="Only .csv and .tsv files are supported")

    content = (await file.read()).decode("utf-8-sig")
    dialect = "excel-tab" if filename.endswith((".tsv", ".txt")) else "excel"
    reader = csv.DictReader(io.StringIO(content), dialect=dialect)

    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="Empty file")

    # Collect all words for duplicate check
    rows = list(reader)
    words = [row.get("word", row.get("Word", "")).strip() for row in rows if row.get("word", row.get("Word", "")).strip()]

    existing = db.query(Flashcard.word).filter(
        Flashcard.user_id == user_id,
        Flashcard.language == user.target_language,
        Flashcard.word.in_(words)
    ).all() if words else []
    existing_words = {row[0] for row in existing}

    created = 0
    skipped = 0
    errors = []

    for i, row in enumerate(rows, start=2):  # start=2: row 1 is header
        word = (row.get("word") or row.get("Word") or "").strip()
        translation = (row.get("translation") or row.get("Translation") or row.get("tłumaczenie") or row.get("Tłumaczenie") or "").strip()
        example = (row.get("example") or row.get("Example") or row.get("przykład") or row.get("Przykład") or "").strip()

        if not word or not translation:
            errors.append(f"Row {i}: missing word or translation")
            continue
        if word in existing_words:
            skipped += 1
            continue

        db.add(Flashcard(
            user_id=user_id,
            word=word,
            translation=translation,
            example_sentence=example or None,
            language=user.target_language,
            cefr_level=user.cefr_level
        ))
        existing_words.add(word)
        created += 1

    db.commit()

    return {
        "success": True,
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "message": f"Imported {created} flashcards, skipped {skipped} duplicates"
    }


# ── Topic-based flashcard generation ─────────────────────────────────────

@router.post("/api/flashcards/{user_id}/generate-from-topic")
async def generate_flashcards_from_topic(
    user_id: int,
    request: GenerateFromTopicRequest,
    db: Session = Depends(get_db),
):
    """Generate flashcard previews from a topic (not saved to DB yet)."""
    topic_id = request.topic_id
    count = request.count
    user = get_user_or_404(db, user_id)
    from backend.models.topic import Topic, TopicItem

    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == user_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Gather context from topic items
    items = db.query(TopicItem).filter(TopicItem.topic_id == topic_id).all()
    item_titles = [item.title for item in items if item.title][:10]

    # Get existing flashcard words to avoid duplicates
    existing_words = {
        row[0] for row in
        db.query(Flashcard.word).filter(
            Flashcard.user_id == user_id,
            Flashcard.language == user.target_language,
        ).all()
    }

    prompt = f"""You are helping a Polish-speaking student learn {user.target_language} at {user.cefr_level} level.

Topic: {topic.name}
Category: {topic.category}
Description: {topic.description or 'N/A'}
Related materials: {', '.join(item_titles) if item_titles else 'N/A'}

Generate {count} useful vocabulary flashcards for this topic.
Avoid these existing words: {', '.join(list(existing_words)[:50])}

For each flashcard provide:
- word: the {user.target_language} word/phrase
- translation: Polish translation
- example: example sentence in {user.target_language}
- example_translation: Polish translation of the example
- gender: grammatical gender if the word is a German noun (der/die/das), or null
- isImportant: boolean indicating if the word is particularly important for mastering this topic (e.g., key conjugations, essential vocabulary that unlocks other concepts)

Return ONLY valid JSON:
{{"flashcards": [
  {{"word": "...", "translation": "...", "example": "...", "example_translation": "...", "gender": "der"|"die"|"das"|null, "isImportant": true/false}},
  ...
]}}
"""

    try:
        result = await _ai_generate_flashcard(prompt)
        if isinstance(result, dict):
            flashcards = result.get("flashcards", [])
        else:
            flashcards = []
    except Exception as e:
        logger.exception("AI flashcard generation from topic failed: %s", e)
        flashcards = []

    return {"flashcards": flashcards}