"""Pydantic schemas for the in-app AI assistant router.

Contract per docs/ASYSTENT_AI_SPEC.md §5 point 3 (approved 2026-09-18,
t_5fa240f2): request carries user_id/question/route/element_context/
selected_text; response is success/answer, same shape as the existing
/api/conversation/question pattern.
"""
from typing import Optional

from pydantic import BaseModel, Field


class ElementContext(BaseModel):
    """Small, safe snippet collected by the frontend's click-to-pick mode
    (D-1) — never a screenshot or full DOM dump."""
    tag: Optional[str] = None
    text: Optional[str] = Field(default=None, max_length=200)
    aria_label: Optional[str] = None
    nearest_heading: Optional[str] = None
    testid: Optional[str] = None


class AssistantAskRequest(BaseModel):
    user_id: Optional[int] = None
    question: str = Field(..., min_length=1, max_length=1000)
    route: Optional[str] = None
    element_context: Optional[ElementContext] = None
    selected_text: Optional[str] = Field(default=None, max_length=2000)
