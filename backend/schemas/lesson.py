"""Pydantic schemas for lesson router."""
from typing import List, Optional

from pydantic import BaseModel


class CompleteLessonRequest(BaseModel):
    user_id: Optional[int] = None
    # Offline replay (same pattern as exercise answers / flashcard reviews):
    # client_event_id makes the replay idempotent; completed_at pins the streak
    # to the day the learner actually finished, not the reconnect day.
    client_event_id: Optional[str] = None
    completed_at: Optional[str] = None


class EvaluateProductionRequest(BaseModel):
    user_id: int
    user_answer: str
    instruction: str
    language: str = "German"
    cefr_level: str = "B1"


class NextLessonRequest(BaseModel):
    user_id: int
    recent_topics: Optional[List[str]] = None


class ConceptFlashcardRequest(BaseModel):
    lesson_id: int
    user_id: int
