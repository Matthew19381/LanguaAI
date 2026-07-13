"""Pydantic schemas for lesson router."""
from typing import List, Optional

from pydantic import BaseModel


class CompleteLessonRequest(BaseModel):
    user_id: Optional[int] = None


class SaveExerciseErrorRequest(BaseModel):
    question: Optional[str] = None
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    exercise_type: Optional[str] = None


class ExerciseErrorRequest(BaseModel):
    user_id: int
    question: str
    user_answer: str
    correct_answer: str
    exercise_type: Optional[str] = "unknown"


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
