"""Pydantic schemas for voice chat router."""
from typing import Optional

from pydantic import BaseModel


class VoiceChatMessageRequest(BaseModel):
    user_id: Optional[int] = None
    message: Optional[str] = None
    language: str = "German"


class VoiceChatPromptResponse(BaseModel):
    prompt: str
    language: str
    has_lesson_today: bool
    due_flashcards: int
    error_count: int


class VoiceChatTextResponse(BaseModel):
    success: bool
    text: str


class VoiceChatVoiceResponse(BaseModel):
    success: bool
    text: str
    audio_base64: str
    message: str = ""
