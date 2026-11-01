"""Pydantic schemas for the mock exam router."""
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class ExamUser(BaseModel):
    user_id: int


class Teil1Message(BaseModel):
    user_id: int
    # stripped first: a turn of spaces only passed min_length=1 (01.11.2026)
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class Teil2Submit(BaseModel):
    user_id: int
    topic_index: int = Field(..., ge=0, le=1)
    transcript: str = Field("", max_length=8000)


class Teil3Submit(BaseModel):
    user_id: int
    answer: str = Field("", max_length=3000)
    feedback: str = Field("", max_length=3000)
