"""
Voice Chat Router — konwersacja przez OpenRouter + generator promptów.
Prompt zawiera: co użytkownik dzisiaj robił, problemy, słownictwo.
"""
import base64
import json
import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.flashcard import Flashcard
from backend.models.lesson import Lesson
from backend.models.test_result import TestResult
from backend.schemas.voice_chat import VoiceChatMessageRequest
from backend.services import audio_service
from backend.services.gemini_service import generate_text, with_model
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/v1/voice-chat/prompt/{user_id}")
def generate_voice_chat_prompt(user_id: int, db: Session = Depends(get_db)):
    """
    Generuj prompt dla Voice Chat/OpenRouter na podstawie dzisiejszej aktywności użytkownika.
    Prompt zawira: lekcję, błędy, słownictwo, plan nauki.
    """
    user = get_user_or_404(db, user_id)

    today = date.today()
    language = user.target_language or "German"

    # 1. Dzisiejsza lekcja
    from sqlalchemy import func
    today_lesson = db.query(Lesson).filter(
        Lesson.user_id == user_id,
        Lesson.is_completed == True,
        Lesson.completed_at != None,
        func.date(Lesson.completed_at) == today
    ).first()

    lesson_info = ""
    if today_lesson and today_lesson.content:
        try:
            content = json.loads(today_lesson.content) if isinstance(today_lesson.content, str) else today_lesson.content
            lesson_info = f"""
## Dzisiejsza lekcja (dzień {today_lesson.day_number}):
- Temat: {content.get('topic', 'Nieznany')}
- Gramatyka: {content.get('key_grammar', 'Nieznane')}
- Cel: {content.get('goal', 'Nieznane')}
"""
            vocab = content.get('vocabulary', [])
            if vocab:
                lesson_info += "- Słownictwo (" + str(len(vocab)) + " słów): " + ", ".join([v.get('word', '') for v in vocab[:10]]) + "\n"
        except (json.JSONDecodeError, TypeError, KeyError):
            lesson_info = "- Brak danych lekcji\n"

    # 2. Błędy z testów (ostatnie 5)
    recent_errors = db.query(TestResult).filter(
        TestResult.user_id == user_id
    ).order_by(TestResult.created_at.desc()).limit(5).all()

    errors_info = ""
    if recent_errors:
        errors_info = "\n## Ostatnie błędy w testach:\n"
        for r in recent_errors:
            if r.errors:
                try:
                    errs = json.loads(r.errors) if isinstance(r.errors, str) else r.errors
                    for e in errs[:3]:
                        errors_info += f"- {e.get('type', 'błąd')}: {e.get('explanation', '')}\n"
                except (json.JSONDecodeError, TypeError):
                    pass

    # 3. Fiszki do powtórki (due today)
    due_flashcards = db.query(Flashcard).filter(
        Flashcard.user_id == user_id,
        Flashcard.is_active == True,
        Flashcard.next_review_date != None,
        Flashcard.next_review_date <= datetime.now(timezone.utc)
    ).limit(10).all()

    flashcard_info = ""
    if due_flashcards:
        flashcard_info = "\n## Fiszki do powtórki dzisiaj (" + str(len(due_flashcards)) + "):\n"
        for f in due_flashcards[:10]:
            flashcard_info += f"- {f.word} = {f.translation}\n"

    # 4. Statystyki błędów
    all_errors = db.query(TestResult).filter(
        TestResult.user_id == user_id,
        TestResult.errors != None
    ).limit(20).all()

    error_categories = {}
    for test in all_errors:
        if test.errors:
            try:
                errs = json.loads(test.errors) if isinstance(test.errors, str) else test.errors
                for e in errs:
                    t = e.get('type', 'unknown')
                    error_categories[t] = error_categories.get(t, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass

    error_summary = ""
    if error_categories:
        sorted_errors = sorted(error_categories.items(), key=lambda x: x[1], reverse=True)
        error_summary = "\n## Najczęstsze błędy:\n"
        for t, cnt in sorted_errors[:5]:
            error_summary += f"- {t}: {cnt} razy\n"

    # Generuj pełny prompt
    prompt = f"""Cześć! Uczę się języka {language}. Pomóż mi dzisiaj.

{lesson_info if lesson_info else "- Brak ukończonej lekcji dzisiaj."}
{errors_info if errors_info else ""}
{error_summary}
{flashcard_info if flashcard_info else ""}

## Moje zapytanie do Ciebie:
Proszę o:
1. Krótkie wyjaśnienie dzisiejszej gramatyki w prostych słowach
2. Przykłady zdań wykorzystujących dzisiejszą gramatykę i słownictwo
3. Pomoc w naprawie najczęstszych błędów (zobacz powyżej)
4. Sugestie, nad czym powinienem/powinnam się skupić w najbliższym czasie

Dziękuję za pomoc!
"""

    return {
        "prompt": prompt,
        "language": language,
        "has_lesson_today": bool(today_lesson),
        "due_flashcards": len(due_flashcards),
        "error_count": len(error_categories),
    }


@router.post("/api/v1/voice-chat/conversation/voice")
@with_model("conversation")
async def voice_chat_voice_conversation(request: VoiceChatMessageRequest):
    """
    Endpoint głosowej rozmowy przez OpenRouter.
    Oczekuje: { "user_id": int, "message": str, "language": str }
    Zwraca: { "success": bool, "text": str, "audio_base64": str }
    """
    user_id = request.user_id
    message = request.message
    language = request.language

    if not user_id or not message:
        raise HTTPException(status_code=400, detail="Missing user_id or message")

    try:
        # Generuj odpowiedź przez OpenRouter
        prompt = f"Odpowiedz w języku {language}. {message}"
        ai_text = await generate_text(prompt)

        # Generuj audio z tekstu (edge-tts)
        audio_bytes = None
        try:
            audio_bytes = await audio_service.generate_audio(ai_text, language)
        except Exception as e:
            logger.warning(f"Audio generation failed: {e}")

        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8') if audio_bytes else ""

        return {
            "success": True,
            "text": ai_text,
            "audio_base64": audio_b64,
            "message": "OpenRouter voice response generated"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OpenRouter voice conversation error: {e}")
        raise HTTPException(status_code=500, detail="Voice conversation failed")


@router.post("/api/v1/voice-chat/conversation/text")
@with_model("conversation")
async def voice_chat_text_conversation(request: VoiceChatMessageRequest):
    """
    Rozmowa tekstowa przez OpenRouter (bez audio).
    """
    user_id = request.user_id
    message = request.message
    language = request.language

    if not user_id or not message:
        raise HTTPException(status_code=400, detail="Missing user_id or message")

    try:
        prompt = f"Odpowiedz w języku {language}. {message}"
        ai_text = await generate_text(prompt)
        return {
            "success": True,
            "text": ai_text,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OpenRouter text conversation error: {e}")
        raise HTTPException(status_code=500, detail="Text conversation failed")
