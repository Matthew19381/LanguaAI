"""POST /api/assistant/ask — in-app AI assistant (docs/ASYSTENT_AI_SPEC.md).

Pilot scope (approved 2026-09-18, t_5fa240f2): only the Lekcja dnia and
Fiszki screens surface the widget calling this endpoint. Answers are always
Polish regardless of the user's target_language, matching the rest of the UI.
"""
import logging

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User
from backend.schemas.assistant import AssistantAskRequest
from backend.services.assistant_service import answer_assistant_question

logger = logging.getLogger(__name__)
router = APIRouter()

_UNAVAILABLE_MESSAGE = "Asystent jest chwilowo niedostępny, spróbuj ponownie."


@router.post("/api/assistant/ask")
async def ask_assistant(request: AssistantAskRequest, db: Session = Depends(get_db)):
    cefr_level = "A2"
    if request.user_id:
        user = db.query(User).filter(User.id == request.user_id).first()
        if user:
            cefr_level = user.cefr_level

    element_context = request.element_context.model_dump() if request.element_context else None

    try:
        answer = await answer_assistant_question(
            question=request.question,
            route=request.route,
            cefr_level=cefr_level,
            element_context=element_context,
            selected_text=request.selected_text,
        )
        return {"success": True, "answer": answer}
    except httpx.RequestError as e:
        logger.error(f"AI service error answering assistant question: {e}")
        return {"success": False, "answer": _UNAVAILABLE_MESSAGE}
    except Exception:
        logger.exception("Unexpected error answering assistant question")
        return {"success": False, "answer": _UNAVAILABLE_MESSAGE}
