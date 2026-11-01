"""Pydantic schemas for test router."""
from typing import List, Literal, Optional

from pydantic import BaseModel


class SubmitTestRequest(BaseModel):
    user_id: int
    test_type: Literal['daily', 'weekly', 'errors']  # 'errors' = "Test z błędów"
    questions: List[dict] = []
    answers: dict
    language: Optional[str] = None
    cefr_level: Optional[str] = None


class PlacementSubmitRequest(BaseModel):
    user_id: int
    answers: List[dict]
    language: Optional[str] = None
