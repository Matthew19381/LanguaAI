"""Pydantic schemas for conversation router."""
from typing import Optional

from pydantic import BaseModel, Field


class StartConversationRequest(BaseModel):
    topic: Optional[str] = None


class MessageRequest(BaseModel):
    session_id: str
    user_message: str = Field(..., max_length=2000)
    user_id: int


class AnalyzeRequest(BaseModel):
    session_id: str
    user_id: Optional[int] = None


class QuestionRequest(BaseModel):
    question: str = Field(..., max_length=500)
    user_id: Optional[int] = None


class AnalyzePastedRequest(BaseModel):
    user_id: int
    pasted_text: str = Field(..., max_length=5000)


class TranslateRequest(BaseModel):
    text: str = Field(..., max_length=200)
    from_lang: str
    to_lang: str
    user_id: int
