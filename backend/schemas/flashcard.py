"""Pydantic schemas for flashcard router."""
from typing import Optional

from pydantic import BaseModel, Field


class ReviewFlashcardRequest(BaseModel):
    rating: int = Field(ge=1, le=4, description="1=Again, 2=Hard, 3=Good, 4=Easy")
    # ── Offline replay ──
    # UUID generated on the device; replaying it is a no-op so a queued review
    # cannot be counted twice.
    client_event_id: Optional[str] = None
    # When the learner actually reviewed the card (ISO 8601), so FSRS schedules
    # from that moment rather than from the reconnect.
    reviewed_at: Optional[str] = None


class HubReviewState(BaseModel):
    """The card's schedule after a review in the hub (System-Glowny stage C)."""
    fsrs_state: str
    fsrs_step: Optional[int] = None
    stability: float = Field(gt=0)
    difficulty: float = Field(ge=1, le=10)
    next_review_date: Optional[str] = None
    repetitions: int = Field(ge=1)
    lapses: int = Field(ge=0, default=0)
    interval_days: int = Field(ge=0, default=1)


class HubReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=4, description="1=Again, 2=Hard, 3=Good, 4=Easy")
    client_event_id: Optional[str] = None
    reviewed_at: Optional[str] = None
    state: HubReviewState


class AddFlashcardRequest(BaseModel):
    word: str
    translation: str
    example_sentence: Optional[str] = None
    example_translation: Optional[str] = None
    isImportant: Optional[bool] = False


class AddFlashcardAIRequest(BaseModel):
    word: str


class ConceptFlashcardRequest(BaseModel):
    lesson_id: int
    concepts: list


class GenerateFromTopicRequest(BaseModel):
    topic_id: int
    count: int = 10


class GenerateFromErrorsRequest(BaseModel):
    user_id: int
    count: int = 10


class BatchFlashcardItem(BaseModel):
    word: str
    translation: str
    example: Optional[str] = None
    example_translation: Optional[str] = None
    gender: Optional[str] = None
    isImportant: Optional[bool] = False


class BatchAddRequest(BaseModel):
    user_id: int
    flashcards: list[BatchFlashcardItem]
