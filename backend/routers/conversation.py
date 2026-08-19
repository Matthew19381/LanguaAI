import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.conversation_session import ConversationSession
from backend.models.test_result import TestResult
from backend.models.user import User
from backend.schemas.conversation import (
    AnalyzePastedRequest,
    AnalyzeRequest,
    MessageRequest,
    QuestionRequest,
    StartConversationRequest,
    TranslateRequest,
)
from backend.services.achievement_service import check_and_award_achievements
from backend.services.gemini_service import generate_text, generate_text_stream, with_model
from backend.services.lesson_generator import (
    analyze_conversation,
    analyze_pasted_conversation,
    answer_language_question,
    generate_conversation_scenario,
)
from backend.services.model_router import get_model_for_task
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_session(db: Session, session_id: str) -> Optional[ConversationSession]:
    """Retrieve a conversation session from the database."""
    return db.query(ConversationSession).filter(ConversationSession.id == session_id).first()


def _save_session(db: Session, session: ConversationSession) -> None:
    """Persist conversation session changes."""
    session.updated_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/api/conversation/start/{user_id}")
async def start_conversation(
    user_id: int,
    request: StartConversationRequest,
    db: Session = Depends(get_db)
):
    user = get_user_or_404(db, user_id)

    # Get recent errors to incorporate
    recent_tests = db.query(TestResult).filter(
        TestResult.user_id == user_id
    ).order_by(TestResult.created_at.desc()).limit(3).all()

    user_errors = []
    for test in recent_tests:
        if test.errors:
            try:
                errors = json.loads(test.errors)
                user_errors.extend(errors[:2])
            except (json.JSONDecodeError, TypeError):
                pass

    topic = request.topic or "everyday conversation"

    try:
        scenario = await generate_conversation_scenario(
            topic=topic,
            cefr_level=user.cefr_level,
            user_errors=user_errors,
            language=user.target_language,
            native_language=user.native_language
        )

        # Create persistent session
        session_id = str(uuid.uuid4())
        opening_line = scenario.get("opening_line", "Hello! Let's start our conversation.")

        conv_session = ConversationSession(
            id=session_id,
            user_id=user_id,
            language=user.target_language,
            native_language=user.native_language,
            cefr_level=user.cefr_level,
            scenario=json.dumps(scenario),
            system_prompt=scenario.get("system_prompt", ""),
            history=json.dumps([{
                "role": "assistant",
                "content": opening_line
            }]),
        )
        db.add(conv_session)
        db.commit()

        return {
            "success": True,
            "session_id": session_id,
            "scenario": scenario.get("scenario", ""),
            "ai_role": scenario.get("ai_role", ""),
            "user_role": scenario.get("user_role", ""),
            "suggested_phrases": scenario.get("suggested_phrases", []),
            "opening_line": opening_line
        }
    except httpx.RequestError as e:
        logger.error(f"AI service error starting conversation: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception:
        logger.exception("Unexpected error starting conversation")
        raise HTTPException(status_code=500, detail="Failed to start conversation")


def _build_reply_prompt(conv_session: ConversationSession, history: list) -> str:
    """Build the reply prompt from session + history (with the new user
    message already appended by the caller). Shared by the plain and
    streaming /message endpoints so the two never drift apart."""
    language = conv_session.language
    cefr_level = conv_session.cefr_level
    system_prompt = conv_session.system_prompt
    scenario = json.loads(conv_session.scenario)

    history_text = "\n".join([
        f"{'You' if msg['role'] == 'assistant' else 'Student'}: {msg['content']}"
        for msg in history[-10:]  # Last 10 messages for context
    ])

    ai_role = scenario.get('ai_role', 'conversation partner')
    return f"""{system_prompt}

Conversation so far:
{history_text}

You are {ai_role}. Reply naturally in {language}, staying in character.
- Keep it at CEFR {cefr_level}: simple, clear, natural phrasing.
- Be warm and engaging, and ALWAYS end your reply with a question or a small
  prompt that invites the student to keep talking, so the conversation keeps
  flowing instead of dying out.
- If the student made a grammar or word-choice error, model the correct form
  naturally inside your own reply — never lecture or break character.
- 1–3 short sentences. Reply ONLY with what {ai_role} actually says, no
  narration, no translations, no meta-commentary."""


@with_model("conversation")
async def _ai_conversation_reply(prompt: str) -> str:
    return await generate_text(prompt)


@router.post("/api/conversation/message")
async def send_message(request: MessageRequest, db: Session = Depends(get_db)):
    conv_session = _get_session(db, request.session_id)
    if not conv_session:
        raise HTTPException(status_code=404, detail="Conversation session not found")

    # Validate session ownership
    if conv_session.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    # Load history, append user message
    history = json.loads(conv_session.history)
    history.append({
        "role": "user",
        "content": request.user_message
    })
    prompt = _build_reply_prompt(conv_session, history)

    try:
        ai_response = await _ai_conversation_reply(prompt)
        ai_response = ai_response.strip()

        # Add AI response to history
        history.append({
            "role": "assistant",
            "content": ai_response
        })

        # Persist updated history
        conv_session.history = json.dumps(history)
        _save_session(db, conv_session)

        return {
            "success": True,
            "response": ai_response,
            "message_count": len(history)
        }
    except httpx.RequestError as e:
        logger.error(f"AI service error in conversation: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception:
        logger.exception("Unexpected error generating conversation response")
        raise HTTPException(status_code=500, detail="Failed to generate response")


@router.post("/api/conversation/message/stream")
async def send_message_stream(request: MessageRequest, db: Session = Depends(get_db)):
    """P2-2 (docs/BACKLOG_UX_2026-08.md): same reply as /message, but as it's
    generated instead of one blocking round-trip. Server-Sent Events, one
    `data:` line per chunk plus a final `done` event; the frontend switches
    on `event.error`/`event.done`/`event.delta`.

    Session lookup/ownership is validated BEFORE the stream starts (still a
    normal 404/403 JSON response) — only generation failures become an SSE
    error event, since by then the response has already committed to
    text/event-stream and the status code can no longer change (same
    constraint OpenRouter's own streaming API documents).

    The post-stream history write uses a FRESH `SessionLocal()` instead of
    the `Depends(get_db)` session above — same pattern as
    `process_lesson_topics_bg` (background tasks). Confirmed by hand (a
    session persisted with the request-scoped `db` here silently vanished
    on refresh): FastAPI's yield-dependency cleanup runs when the route
    handler function *returns* `StreamingResponse(...)`, not after the
    generator finishes — by the time this code runs, `db` may already be
    closed, and writes to a closed/reset session can silently no-op instead
    of raising.
    """
    conv_session = _get_session(db, request.session_id)
    if not conv_session:
        raise HTTPException(status_code=404, detail="Conversation session not found")
    if conv_session.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    history = json.loads(conv_session.history)
    history.append({"role": "user", "content": request.user_message})
    prompt = _build_reply_prompt(conv_session, history)
    model = get_model_for_task("conversation")
    session_id = request.session_id

    async def event_stream():
        full_text = ""
        try:
            async for chunk in generate_text_stream(prompt, model=model):
                full_text += chunk
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Streaming conversation error: {e}")
            # Nothing usable was generated (or it broke mid-stream) — don't
            # persist a partial/garbled reply into the session history.
            yield f"data: {json.dumps({'error': 'Failed to generate response'})}\n\n"
            return

        ai_response = full_text.strip()
        history.append({"role": "assistant", "content": ai_response})

        from backend.database import SessionLocal
        write_db = SessionLocal()
        try:
            fresh_session = _get_session(write_db, session_id)
            if fresh_session:
                fresh_session.history = json.dumps(history)
                _save_session(write_db, fresh_session)
        finally:
            write_db.close()

        yield f"data: {json.dumps({'done': True, 'response': ai_response, 'message_count': len(history)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/conversation/analyze")
async def analyze_session(
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
):
    conv_session = _get_session(db, request.session_id)
    if not conv_session:
        raise HTTPException(status_code=404, detail="Conversation session not found")

    # Verify ownership
    if request.user_id and conv_session.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    try:
        history = json.loads(conv_session.history)

        # Filter to only user messages for analysis
        user_messages = [msg for msg in history if msg["role"] == "user"]

        if not user_messages:
            return {
                "success": True,
                "summary": "No messages to analyze yet.",
                "errors": [],
                "vocabulary_used": [],
                "recommendations": ["Start the conversation first!"],
                "score": 0
            }

        analysis = await analyze_conversation(
            conversation_history=history,
            cefr_level=conv_session.cefr_level,
            language=conv_session.language,
            native_language=conv_session.native_language
        )

        # Save errors to DB if user_id provided
        if request.user_id:
            user = db.query(User).filter(User.id == request.user_id).first()
            if user:
                errors = analysis.get("errors", [])
                test_result = TestResult(
                    user_id=request.user_id,
                    test_type="conversation",
                    score=analysis.get("score", 0),
                    answers=json.dumps({"messages": len(user_messages)}),
                    errors=json.dumps(errors),
                    cefr_level=conv_session.cefr_level,
                    language=conv_session.language
                )
                db.add(test_result)

                # Award XP for conversation practice
                xp = min(30, int(analysis.get("score", 0) * 0.3))
                user.total_xp += xp
                db.commit()
                analysis["xp_earned"] = xp

                # Check achievements after conversation XP award
                newly_awarded = check_and_award_achievements(user, db)
                analysis["new_achievements"] = newly_awarded

        # Delete session after all DB operations succeeded
        db.delete(conv_session)
        db.commit()

        return {
            "success": True,
            **analysis
        }
    except httpx.RequestError as e:
        logger.error(f"AI service error analyzing conversation: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception:
        logger.exception("Unexpected error analyzing conversation")
        raise HTTPException(status_code=500, detail="Failed to analyze conversation")


@router.post("/api/conversation/question")
async def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_db)
):
    cefr_level = "B1"
    language = settings.TARGET_LANGUAGE
    native_language = settings.NATIVE_LANGUAGE

    if request.user_id:
        user = db.query(User).filter(User.id == request.user_id).first()
        if user:
            cefr_level = user.cefr_level
            language = user.target_language
            native_language = user.native_language

    try:
        answer = await answer_language_question(
            question=request.question,
            cefr_level=cefr_level,
            language=language,
            native_language=native_language
        )
        return {
            "success": True,
            "question": request.question,
            "answer": answer
        }
    except httpx.RequestError as e:
        logger.error(f"AI service error answering question: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception:
        logger.exception("Unexpected error answering question")
        raise HTTPException(status_code=500, detail="Failed to answer question")


@with_model("lesson")
async def _ai_translate(prompt: str) -> str:
    return await generate_text(prompt)


@router.post("/api/conversation/translate")
async def translate_word(request: TranslateRequest, db: Session = Depends(get_db)):
    """Translate a word or short phrase. Returns only the translation, no explanation."""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prompt = (
        f'Translate from {request.from_lang} to {request.to_lang}: "{request.text}"\n'
        f'Reply with the translation ONLY. No explanations, no alternatives, no context.'
    )
    try:
        result = await _ai_translate(prompt)
        return {"success": True, "translation": result.strip()}
    except httpx.RequestError as e:
        logger.error(f"AI service error in translation: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception:
        logger.exception("Unexpected translation error")
        raise HTTPException(status_code=500, detail="Translation failed")


@router.post("/api/conversation/analyze-text")
async def analyze_pasted_text(
    request: AnalyzePastedRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not request.pasted_text.strip():
        raise HTTPException(status_code=400, detail="No text provided")

    try:
        analysis = await analyze_pasted_conversation(
            pasted_text=request.pasted_text,
            cefr_level=user.cefr_level,
            language=user.target_language,
            native_language=user.native_language
        )

        # Save to TestResult
        errors = analysis.get("errors", [])
        test_result = TestResult(
            user_id=request.user_id,
            test_type="conversation_paste",
            score=analysis.get("score", 0),
            answers=json.dumps({"source": "pasted_text", "length": len(request.pasted_text)}),
            errors=json.dumps(errors),
            cefr_level=user.cefr_level,
            language=user.target_language
        )
        db.add(test_result)

        xp = min(20, int(analysis.get("score", 0) * 0.2))
        user.total_xp += xp
        db.commit()

        analysis["xp_earned"] = xp
        # Check achievements after pasted-text analysis XP award
        analysis["new_achievements"] = check_and_award_achievements(user, db)
        return {"success": True, **analysis}
    except HTTPException:
        raise
    except httpx.RequestError as e:
        logger.error(f"AI service error analyzing pasted text: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception:
        logger.exception("Unexpected error analyzing pasted text")
        raise HTTPException(status_code=500, detail="Failed to analyze text")
