"""Pydantic schemas for pronunciation router."""
from typing import Optional

from pydantic import BaseModel


class AnalyzePronunciationRequest(BaseModel):
    user_id: int
    target_text: str
    audio_filename: Optional[str] = None
