"""Pydantic schemas for flashcard router."""
from typing import Optional

from pydantic import BaseModel, Field


class ReviewFlashcardRequest(BaseModel):
    rating: int = Field(ge=1, le=4, description="1=Again, 2=Hard, 3=Good, 4=Easy")


class AddFlashcardRequest(BaseModel):
    word: str
    translation: str
    example_sentence: Optional[str] = None
    isImportant: Optional[bool] = False


class AddFlashcardAIRequest(BaseModel):
    word: str


class ConceptFlashcardRequest(BaseModel):
    lesson_id: int
    concepts: list


class GenerateFromTopicRequest(BaseModel):
    topic_id: int
    count: int = 10
