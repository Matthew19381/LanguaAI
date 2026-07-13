"""Pydantic schemas for test router."""
from pydantic import BaseModel
from typing import Optional, List


class SubmitTestRequest(BaseModel):
    user_id: int
    test_type: str  # 'daily' or 'weekly'
    questions: List[dict] = []
    answers: dict
    language: Optional[str] = None
    cefr_level: Optional[str] = None


class PlacementSubmitRequest(BaseModel):
    user_id: int
    answers: List[dict]
    language: Optional[str] = None
