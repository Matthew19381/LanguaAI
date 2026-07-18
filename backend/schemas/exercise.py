"""Pydantic schemas for the exercise bank router."""
from typing import Optional

from pydantic import BaseModel


class AnswerExerciseRequest(BaseModel):
    user_id: int
    answer: str
    # Optional self-assessment (1=Again, 2=Hard, 3=Good, 4=Easy). When omitted the
    # rating is derived from whether the submitted answer matched.
    rating: Optional[int] = None
    # ── Offline replay ──
    # UUID generated on the device. Replaying the same id is a no-op, so a queued
    # answer can be retried safely without double-counting the review.
    client_event_id: Optional[str] = None
    # When the learner actually answered (ISO 8601). Used instead of "now" so a
    # queued answer schedules from the moment it happened.
    answered_at: Optional[str] = None


class GenerateVariantsRequest(BaseModel):
    skills: Optional[list[str]] = None  # defaults to the learner's weakest skills
    per_skill: int = 2
