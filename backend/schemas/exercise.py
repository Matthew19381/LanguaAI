"""Pydantic schemas for the exercise bank router."""
from typing import Optional

from pydantic import BaseModel


class AnswerExerciseRequest(BaseModel):
    user_id: int
    answer: str
    # Optional self-assessment (1=Again, 2=Hard, 3=Good, 4=Easy). When omitted the
    # rating is derived from whether the submitted answer matched.
    rating: Optional[int] = None


class GenerateVariantsRequest(BaseModel):
    skills: Optional[list[str]] = None  # defaults to the learner's weakest skills
    per_skill: int = 2
