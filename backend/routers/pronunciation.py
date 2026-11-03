import logging
import re

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.gemini_service import generate_json, with_model
from backend.utils import get_user_or_404

try:
    from backend.services.pronunciation_service import score_pronunciation, transcribe_audio
    PRONUNCIATION_AVAILABLE = True
except (ImportError, OSError):
    PRONUNCIATION_AVAILABLE = False
    transcribe_audio = None
    score_pronunciation = None

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/pronunciation/analyze")
async def analyze_pronunciation(
    audio: UploadFile = File(...),
    target_text: str = Form(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Transcribe uploaded audio and compare to target_text. Returns pronunciation score."""
    if not PRONUNCIATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Pronunciation service unavailable: faster-whisper not installed.")
    user = get_user_or_404(db, user_id)

    # Limit audio upload to 10 MB to prevent memory exhaustion
    MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10 MB
    audio_bytes = await audio.read(MAX_AUDIO_SIZE + 1)   # never more than the limit in memory
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file received.")
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail="Audio file too large. Maximum size is 10 MB.")

    # Determine format from content type or filename
    content_type = audio.content_type or ""
    filename = audio.filename or ""
    if "webm" in content_type or "webm" in filename:
        fmt = "webm"
    elif "ogg" in content_type or "ogg" in filename:
        fmt = "ogg"
    elif "mp4" in content_type or "m4a" in filename:
        fmt = "mp4"
    elif "wav" in content_type or "wav" in filename:
        fmt = "wav"
    else:
        fmt = "webm"  # default for MediaRecorder

    try:
        from backend.services.pronunciation_service import LANGUAGE_CODES
        lang_code = LANGUAGE_CODES.get(user.target_language, "de")
        # Whisper is CPU-bound (and loads the model on first use): in a thread, so the
        # rest of the app keeps answering meanwhile
        transcribed = await run_in_threadpool(transcribe_audio, audio_bytes, audio_format=fmt, language=lang_code)
        result = score_pronunciation(transcribed, target_text)
        result["language"] = user.target_language
        return {"success": True, **result}
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Pronunciation service unavailable. Please run: pip install faster-whisper==1.0.3"
        )
    except ValueError as e:   # recording that cannot be decoded
        logger.warning("Pronunciation audio rejected: %s", e)
        raise HTTPException(status_code=400, detail="Nie udało się odczytać nagrania. Nagraj jeszcze raz.")
    except (httpx.RequestError, OSError) as e:
        logger.exception("Error in pronunciation analysis: %s", e)
        raise HTTPException(status_code=500, detail="Failed to analyze pronunciation")


MAX_PHRASES = 30
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _lesson_sentences(content: dict) -> list[dict]:
    """German sentences of one lesson with their Polish translation where the lesson
    has one: vocabulary examples, grammar examples, the recall text, dialogue lines.
    Until 3.11.2026 only vocab["example"] (the key is "example_sentence") and the
    dialogue (new lessons have none) were read, so one saw only 3 fixed sentences."""
    out = []
    for v in content.get("vocabulary") or []:
        if not isinstance(v, dict):
            continue
        text = (v.get("example_sentence") or v.get("example") or "").strip()
        if text:
            out.append({"text": text, "translation": (v.get("example_translation") or "").strip(),
                        "source": f"Słówko: {v.get('word', '')}".strip()})
    g = content.get("grammar")
    for e in (g.get("examples") or []) if isinstance(g, dict) else []:
        if isinstance(e, dict) and (e.get("sentence") or "").strip():
            out.append({"text": e["sentence"].strip(),
                        "translation": str(e.get("translation") or "").split(" (")[0].strip(),
                        "source": "Gramatyka"})
    of = content.get("output_forcing")
    if isinstance(of, dict) and (of.get("text") or "").strip():
        for sentence in _SENTENCE_END.split(of["text"].strip()):
            if sentence.strip():
                out.append({"text": sentence.strip(), "translation": "", "source": "Tekst lekcji"})
    dialogue = content.get("dialogue")
    lines = dialogue.get("lines", []) if isinstance(dialogue, dict) else dialogue if isinstance(dialogue, list) else []
    for line in lines:
        if isinstance(line, dict) and (line.get("text") or "").strip():
            out.append({"text": line["text"].strip(), "translation": (line.get("translation") or "").strip(),
                        "source": "Dialog"})
    return out


@router.get("/api/pronunciation/phrases/{user_id}")
async def get_practice_phrases(user_id: int, db: Session = Depends(get_db)):
    """Sentences to practise: from the learner's lessons (newest first) and the
    example sentences of their flashcards, without repeats."""
    import json

    from backend.models.flashcard import Flashcard
    from backend.models.lesson import Lesson

    user = get_user_or_404(db, user_id)
    lessons = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.language == user.target_language,
    ).order_by(Lesson.created_at.desc()).limit(10).all()

    phrases, seen = [], set()

    def add(item):
        key = item["text"].lower()
        if key not in seen and len(phrases) < MAX_PHRASES:
            seen.add(key)
            phrases.append(item)

    for lesson in lessons:
        try:
            content = json.loads(lesson.content) if isinstance(lesson.content, str) else (lesson.content or {})
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(content, dict):
            for item in _lesson_sentences(content):
                add(item)

    cards = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.language == user.target_language,
        Flashcard.example_sentence.isnot(None),
    ).order_by(Flashcard.created_at.desc()).limit(MAX_PHRASES).all()
    for c in cards:
        if (c.example_sentence or "").strip():
            add({"text": c.example_sentence.strip(), "translation": (c.example_translation or "").strip(),
                 "source": f"Fiszka: {c.word}"})

    if not phrases:
        phrases = [
            {"text": "Hallo, wie geht es dir?", "translation": "Cześć, jak się masz?", "source": "Podstawowe zwroty"},
            {"text": "Ich lerne gerade Deutsch.", "translation": "Uczę się teraz niemieckiego.", "source": "Podstawowe zwroty"},
            {"text": "Können Sie mir bitte helfen?", "translation": "Czy może mi Pan/Pani pomóc?", "source": "Podstawowe zwroty"},
        ]

    return {"language": user.target_language, "phrases": phrases}


_POLISH_LETTERS = set("ąćęłńśźżĄĆĘŁŃŚŹŻ")


@with_model("test")
async def _generate_phrases_json(prompt: str) -> dict:
    return await generate_json(prompt)


@router.post("/api/pronunciation/generate/{user_id}")
async def generate_practice_phrases(user_id: int, count: int = 5, db: Session = Depends(get_db)):
    """New practice sentences from the model, as JSON checked in code. Until 3.11.2026
    the page asked the tutor chat and split its free-text answer into lines (headings
    and Polish lines became "sentences"), and a failure was silently ignored."""
    import json

    from backend.models.lesson import Lesson

    user = get_user_or_404(db, user_id)
    count = max(1, min(count, 10))
    lesson = db.query(Lesson).filter(Lesson.user_id == user_id, Lesson.language == user.target_language) \
        .order_by(Lesson.created_at.desc()).first()
    words = []
    if lesson:
        try:
            content = json.loads(lesson.content) if isinstance(lesson.content, str) else (lesson.content or {})
            words = [v.get("word", "") for v in content.get("vocabulary") or [] if isinstance(v, dict)][:12]
        except (json.JSONDecodeError, TypeError, AttributeError):
            words = []
    prompt = f"""Write {count} different {user.target_language} sentences for pronunciation practice
for a {user.native_language} speaker at CEFR {user.cefr_level or 'A2'}.
Each sentence: natural, everyday, 5 to 14 words, with sounds that are hard for {user.native_language} speakers
(e.g. ü, ö, ä, ch, r, final -er, long vowels). {('Use some of these lesson words: ' + ', '.join(w for w in words if w)) if words else ''}

Return ONLY valid JSON:
{{"phrases": [{{"text": "sentence in {user.target_language}", "translation": "{user.native_language} translation"}}]}}"""
    try:
        data = await _generate_phrases_json(prompt)
    except Exception as e:
        logger.warning("Pronunciation phrases not generated: %s", e)
        raise HTTPException(status_code=503, detail="Nie udało się wygenerować zdań (AI niedostępne). Spróbuj później.")
    items = data.get("phrases") if isinstance(data, dict) else None
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        text = str(it.get("text") or "").strip()
        n = len(text.split())
        if not text or not (3 <= n <= 20) or len(text) > 200 or _POLISH_LETTERS & set(text):
            continue
        out.append({"text": text, "translation": str(it.get("translation") or "").strip(), "source": "AI"})
    if not out:
        raise HTTPException(status_code=502, detail="AI zwróciło zdania w złym formacie. Spróbuj jeszcze raz.")
    return {"language": user.target_language, "phrases": out[:count]}
